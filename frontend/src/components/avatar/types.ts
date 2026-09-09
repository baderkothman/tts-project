/** Bayan's finite states. This is the whole vocabulary the avatar can be in —
 * every screen that shows Bayan picks one of these, never ad-hoc booleans.
 * See `useAvatarController` for how app state maps onto this set, and
 * `docs/brand/avatar/AVATAR.md` for the full state-machine diagram and the
 * emotions/poses this first pass intentionally leaves for later. */
export type AvatarState =
  | "sleep" // not yet connected to the backend
  | "error" // health check failed, or the last generation errored
  | "thinking" // model loading, or a generation request is in flight
  | "talking" // streaming synthesis is actively playing audio
  | "success" // a result just arrived (transient, settles back to idle)
  | "idle"; // ready and waiting
