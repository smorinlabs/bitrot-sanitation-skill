// brot plugin for OpenCode (V2 server plugin, no dependencies).
// Install: copy or symlink this file into ~/.config/opencode/plugins/.
// Every handler forwards the object OpenCode gave it to
// `brot hook opencode <event>` on stdin and never throws into OpenCode.

const startedRoots = new Set(); // sessions brot has seen start
const pendingContext = new Map(); // sessionID -> session-start text not yet shown

async function brot(event, payload, wait) {
  const input = JSON.stringify(payload);
  try {
    if (globalThis.Bun && typeof globalThis.Bun.spawn === "function") {
      const p = globalThis.Bun.spawn(["brot", "hook", "opencode", event], {
        stdin: "pipe",
        stdout: wait ? "pipe" : "ignore",
        stderr: "ignore",
      });
      p.stdin.write(input);
      p.stdin.end();
      if (!wait) return "";
      const out = await new Response(p.stdout).text();
      await p.exited;
      return out;
    }
    const { spawn } = await import("node:child_process");
    return await new Promise((resolve) => {
      const p = spawn("brot", ["hook", "opencode", event], {
        stdio: ["pipe", wait ? "pipe" : "ignore", "ignore"],
      });
      let out = "";
      p.on("error", () => resolve(""));
      if (wait) p.stdout.on("data", (d) => (out += d));
      p.on("close", () => resolve(wait ? out : ""));
      p.stdin.on("error", () => {});
      p.stdin.end(input);
    });
  } catch {
    return ""; // brot missing or failed: never break the session (DG-01)
  }
}

function keepContext(sessionID, out) {
  for (const line of out.split("\n")) {
    try {
      const v = JSON.parse(line);
      if (v && typeof v.context === "string" && v.context) pendingContext.set(sessionID, v.context);
    } catch {}
  }
}

// OpenCode does not deliver a root session's own session.created to plugins,
// so the first sign of a root session starts it.
async function startRoot(sessionID) {
  if (!sessionID || startedRoots.has(sessionID)) return;
  startedRoots.add(sessionID);
  keepContext(sessionID, await brot("session-created", { data: { sessionID } }, true));
}

export default {
  id: "brot",
  async setup(ctx) {
    const controller = new AbortController();

    void (async () => {
      try {
        for await (const ev of ctx.event.subscribe({ signal: controller.signal })) {
          const type = ev && ev.type;
          if (type === "session.created") {
            const id = ev.data && ev.data.sessionID;
            if (id) startedRoots.add(id);
            if (ev.data && ev.data.parentID) void brot("session-created", ev, false);
            else if (id) keepContext(id, await brot("session-created", ev, true));
          } else if (type === "session.deleted") {
            void brot("session-deleted", ev, false);
          } else if (typeof type === "string" && type.startsWith("session.execution.") && type !== "session.execution.started") {
            void brot("execution-ended", ev, false);
          }
        }
      } catch {}
    })();

    ctx.tool.hook("execute.before", async (e) => {
      if (e && e.tool === "shell") void brot("pre-tool", e, false);
    });

    ctx.tool.hook("execute.after", async (e) => {
      if (!e) return;
      await startRoot(e.sessionID);
      const directory = ctx.location && ctx.location.directory;
      void brot("tool-after", directory ? { ...e, directory } : e, false);
    });

    ctx.session.hook("fork", async (e) => {
      if (!e || !e.sessionID) return;
      startedRoots.add(e.sessionID);
      keepContext(e.sessionID, await brot("session-forked", { sessionID: e.sessionID }, true));
    });

    ctx.session.hook("context", (e) => {
      const id = e && (e.sessionID || (e.session && e.session.id));
      const text = id && pendingContext.get(id);
      if (!text || !Array.isArray(e.system)) return;
      e.system.push({ type: "text", text });
      pendingContext.delete(id);
    });

    return () => controller.abort();
  },
};
