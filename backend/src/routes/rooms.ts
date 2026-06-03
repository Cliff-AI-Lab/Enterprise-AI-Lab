import { Hono } from "hono";
import { randomUUID } from "node:crypto";
import { createCollaborationRoom, listRooms, listMessages, db, type RoomRunMode } from "../db.js";

export const roomsRoute = new Hono();

function isRoomRunMode(value: unknown): value is RoomRunMode {
  return value === "sequential" || value === "parallel" || value === "loop";
}

roomsRoute.get("/", (c) => {
  return c.json({ rooms: listRooms() });
});

roomsRoute.post("/", async (c) => {
  const body = (await c.req.json()) as {
    id?: string;
    title?: string;
    memberIds?: unknown;
    mode?: unknown;
  };
  const title = body.title?.trim();
  if (!title) return c.json({ error: "title required" }, 400);

  const memberIds = Array.isArray(body.memberIds)
    ? [...new Set(body.memberIds.filter((id): id is string => typeof id === "string" && /^[a-z0-9_-]+$/i.test(id)))]
    : [];
  if (memberIds.length === 0) return c.json({ error: "memberIds required" }, 400);

  const unknownAgents = memberIds.filter(
    (id) => !db.prepare(`SELECT 1 FROM agent_profiles WHERE id = ?`).get(id),
  );
  if (unknownAgents.length > 0) {
    return c.json({ error: `unknown agents: ${unknownAgents.join(", ")}` }, 400);
  }

  let runMode: RoomRunMode | undefined;
  if (body.mode !== undefined && body.mode !== null) {
    if (!isRoomRunMode(body.mode)) {
      return c.json({ error: "mode must be sequential, parallel, or loop" }, 400);
    }
    runMode = body.mode;
  }

  const id = body.id && /^[a-z0-9_-]+$/i.test(body.id) ? body.id : `room-${randomUUID()}`;
  try {
    createCollaborationRoom({ id, title, memberIds, runMode });
  } catch (err) {
    const e = err as { code?: string; errcode?: number; errstr?: string; message?: string };
    const isUniqueViolation =
      e.errcode === 1555 ||
      e.errcode === 2067 ||
      (typeof e.errstr === "string" && /UNIQUE|PRIMARY KEY/i.test(e.errstr)) ||
      (typeof e.message === "string" && /UNIQUE|PRIMARY KEY/i.test(e.message));
    if (isUniqueViolation) {
      return c.json({ error: "room already exists" }, 409);
    }
    console.warn(`[rooms] createCollaborationRoom failed:`, e.message ?? e);
    return c.json({ error: e.message ?? "failed to create room" }, 500);
  }

  return c.json(
    { room: { id, kind: "room", title, agentId: null, memberIds, runMode: runMode ?? null, lastMessage: null, lastActivityAt: null } },
    201,
  );
});

roomsRoute.get("/:roomId/messages", (c) => {
  const roomId = c.req.param("roomId");
  return c.json({ messages: listMessages(roomId) });
});
