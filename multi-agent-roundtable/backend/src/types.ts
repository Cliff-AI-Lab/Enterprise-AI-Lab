export interface ServerAgent {
  id: string;
  name: string;
  role: string;
  profile: string;
  model: string;
  hidden: boolean;
  emoji?: string;
  color: string;
  initials: string;
}

export interface ServerRoom {
  id: string;
  kind: "agent" | "room";
  title: string;
  agentId?: string;
  memberIds: string[];
  lastMessage?: string;
  unread?: number;
}

export interface ServerMessage {
  id: string;
  roomId: string;
  sender: "human" | "agent" | "system";
  agentId?: string;
  body: string;
  createdAt: number;
}

export interface User {
  id: string;
  displayName: string;
}
