// node --test tests/opencode.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";

const calls = [];
let failSpawn = false;
globalThis.Bun = {
  spawn(argv) {
    if (failSpawn) throw new Error("ENOENT");
    let input = "";
    const rec = { argv, get payload() { return JSON.parse(input); } };
    calls.push(rec);
    const out = argv[3] === "session-created" || argv[3] === "session-forked" ? '{"context":"2 blockers cleared"}\n' : "";
    return {
      stdin: { write: (s) => (input += s), end() {} },
      stdout: new Blob([out]).stream(),
      exited: Promise.resolve(0),
    };
  },
};
const plugin = (await import("../plugins/brot/opencode/brot.js")).default;

function fakeCtx(events) {
  const hooks = {};
  return {
    hooks,
    location: { directory: "/w" },
    event: { subscribe: () => (async function* () { for (const e of events) yield e; })() },
    tool: { hook: (n, f) => (hooks["tool." + n] = f) },
    session: { hook: (n, f) => (hooks["session." + n] = f) },
  };
}
const tick = () => new Promise((r) => setTimeout(r, 10));
const names = () => calls.map((c) => c.argv.join(" "));

test("every call uses the literal argv brot doctor recognises", async () => {
  calls.length = 0;
  const ctx = fakeCtx([
    { type: "session.created", data: { sessionID: "child", parentID: "root" } },
    { type: "session.execution.started", data: { sessionID: "root" } },
    { type: "session.execution.interrupted", data: { sessionID: "root" } },
    { type: "session.deleted", data: { sessionID: "root" } },
    { type: "session.idle", data: { sessionID: "root" } },
  ]);
  await plugin.setup(ctx);
  await tick();
  assert.deepEqual(names(), [
    "brot hook opencode session-created",
    "brot hook opencode execution-ended",
    "brot hook opencode session-deleted",
  ]);
  assert.equal(calls[0].payload.data.parentID, "root");
});

test("first tool of a root session starts it, adds directory, and injects context once", async () => {
  calls.length = 0;
  const ctx = fakeCtx([]);
  await plugin.setup(ctx);
  await ctx.hooks["tool.execute.after"]({ sessionID: "r1", tool: "shell", input: { command: "ls" } });
  await ctx.hooks["tool.execute.after"]({ sessionID: "r1", tool: "write", input: { path: "a" } });
  await tick();
  assert.deepEqual(names(), [
    "brot hook opencode session-created",
    "brot hook opencode tool-after",
    "brot hook opencode tool-after",
  ]);
  assert.deepEqual(calls[0].payload, { data: { sessionID: "r1" } });
  assert.equal(calls[1].payload.directory, "/w");
  const e = { sessionID: "r1", system: [] };
  ctx.hooks["session.context"](e);
  ctx.hooks["session.context"](e);
  assert.deepEqual(e.system, [{ type: "text", text: "2 blockers cleared" }]);
});

test("pre-tool only for the shell tool; fork forwards the new session ID", async () => {
  calls.length = 0;
  const ctx = fakeCtx([]);
  await plugin.setup(ctx);
  await ctx.hooks["tool.execute.before"]({ sessionID: "r1", tool: "read" });
  await ctx.hooks["tool.execute.before"]({ sessionID: "r1", tool: "shell" });
  await ctx.hooks["session.fork"]({ sessionID: "f1" });
  await tick();
  assert.deepEqual(names(), ["brot hook opencode pre-tool", "brot hook opencode session-forked"]);
  assert.deepEqual(calls[1].payload, { sessionID: "f1" });
  const e = { sessionID: "f1", system: [] };
  ctx.hooks["session.context"](e);
  assert.deepEqual(e.system, [{ type: "text", text: "2 blockers cleared" }]);
});

test("a missing brot never throws into OpenCode", async () => {
  failSpawn = true;
  const ctx = fakeCtx([{ type: "session.deleted", data: { sessionID: "x" } }]);
  await plugin.setup(ctx);
  await ctx.hooks["tool.execute.after"]({ sessionID: "r9", tool: "shell" });
  await ctx.hooks["session.fork"]({ sessionID: "f9" });
  await tick();
  failSpawn = false;
});

// P18: clearedFrom on a new root session, only when exactly one other live
// root exists in this plugin instance. A fresh module copy per test keeps the
// module-level session state separate.
async function freshPlugin(tag) {
  return (await import(`../plugins/brot/opencode/brot.js?p18=${tag}`)).default;
}

test("a /clear in one window names the session it replaced", async () => {
  const p = await freshPlugin("one-window");
  calls.length = 0;
  const ctx = fakeCtx([
    { type: "session.created", data: { sessionID: "A" } },
    { type: "session.created", data: { sessionID: "B" } },
    { type: "session.created", data: { sessionID: "C" } },
  ]);
  await p.setup(ctx);
  await tick();
  const created = calls.filter((c) => c.argv[3] === "session-created").map((c) => c.payload);
  assert.equal(created[0].clearedFrom, undefined);
  assert.equal(created[1].clearedFrom, "A");
  assert.equal(created[2].clearedFrom, "B");
});

test("two live roots in one server send no clearedFrom", async () => {
  const p = await freshPlugin("shared-server");
  calls.length = 0;
  const ctx = fakeCtx([
    { type: "session.created", data: { sessionID: "X" } },
  ]);
  await p.setup(ctx);
  await tick(); // X's session.created is handled first, as a real server sends it
  // A second window's session shows up through its first tool event.
  await ctx.hooks["tool.execute.after"]({ sessionID: "Y", tool: "shell" });
  await tick();
  const ctx2 = fakeCtx([{ type: "session.created", data: { sessionID: "Z" } }]);
  await p.setup(ctx2);
  await tick();
  const z = calls.filter((c) => c.argv[3] === "session-created").map((c) => c.payload).at(-1);
  assert.equal(z.data.sessionID, "Z");
  assert.equal(z.clearedFrom, undefined);
});

test("a deleted root is not taken as the one /clear replaced", async () => {
  const p = await freshPlugin("deleted");
  calls.length = 0;
  const ctx = fakeCtx([
    { type: "session.created", data: { sessionID: "A" } },
    { type: "session.deleted", data: { sessionID: "A" } },
    { type: "session.created", data: { sessionID: "B" } },
  ]);
  await p.setup(ctx);
  await tick();
  const b = calls.filter((c) => c.argv[3] === "session-created").map((c) => c.payload).at(-1);
  assert.equal(b.clearedFrom, undefined);
});
