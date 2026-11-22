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
