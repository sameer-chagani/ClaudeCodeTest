# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Games

No build step. Open any HTML file directly in a browser:
```
open tictactoe.html
open shooter.html
```

## Git Workflow

**Every time work is completed, commit and push immediately.** This is mandatory — never leave finished work uncommitted. The goal is that GitHub always reflects the current working state of the project so nothing is ever lost.

- Commit after each logical unit of work (a new feature, a bug fix, a content change)
- Never batch multiple unrelated changes into one commit
- Always push after committing — local-only commits are not safe enough
- Write commit messages in the imperative, describing *what* the change does and *why* if non-obvious

```
git add <files>
git commit -m "Add shield power-up with 5s duration and visual ring indicator"
git push
```

Remote: `https://github.com/sameer-chagani/ClaudeCodeTest`

## Project Structure

Two self-contained single-file games. All HTML, CSS, and JS live in one file each — no external dependencies, no build tools, no frameworks.

- `tictactoe.html` — Tic Tac Toe (DOM-based, minimax AI, player name modal)
- `shooter.html` — Pixel Assault top-down shooter (Canvas-based)

## shooter.html Architecture

The script is organized into 12 labelled sections in order:

| Section | Contents |
|---------|----------|
| 1 | Constants (`W`, `H`, `PLAYER_SPEED`, etc.) and the `PAL` color palette object |
| 2 | Canvas setup (`ctx`) |
| 3 | `game`, `player`, `bullets[]`, `enemies[]`, `particles[]`, `keys`, `mouse` state |
| 4 | `DEFINED_LEVELS[]` array and `getLevelConfig(n)` for infinite scaling |
| 5 | Entity factories: `createEnemy`, `createBullet`, `createParticle`, `explosion`, `muzzleFlash`, `scorePopup` |
| 6 | Spawn queue: `buildSpawnQueue` (Fisher-Yates shuffle), `trySpawn` |
| 7 | Input event listeners (keydown/keyup/mousemove/click) |
| 8 | Update functions: `updatePlayer`, `updateBullets`, `updateEnemies`, `updateParticles`, `updateCollisions`, `checkLevelComplete` |
| 9 | Draw functions: `drawBackground`, `drawPlayer`, `drawEnemies` (+ per-type helpers), `drawBullets`, `drawParticles`, `drawHUD`, `drawMenu`, `drawLevelComplete`, `drawGameOver`, `drawCrosshair` |
| 10 | State management: `startGame`, `loadLevel`, `advanceLevel`, `triggerGameOver` |
| 11 | `gameLoop(ts)` — the `requestAnimationFrame` loop |
| 12 | Boot (kicks off the loop) |

### Game States
`STATE.MENU` → `STATE.PLAYING` → `STATE.LVLCOMPLETE` → `STATE.PLAYING` (loop) or `STATE.GAMEOVER`

### Entity Conventions
All entities (`bullets`, `enemies`, `particles`) are plain objects with an `active` boolean. Mark `active = false` to destroy; filter the array after each update loop. Never splice mid-iteration.

```js
// Pattern used throughout:
entities.forEach(e => update(e));
entities = entities.filter(e => e.active);
```

### Canvas Rotation Pattern
All rotating entities are drawn as if "facing right" (angle = 0 points along +x). Use `save/translate/rotate/restore` around every rotated draw:

```js
ctx.save();
ctx.translate(entity.x, entity.y);
ctx.rotate(entity.angle);  // atan2 result, 0 = rightward
// draw at local coords — (0,0) is entity center, right = forward
ctx.restore();
```

### Frame-Rate Independence
All positional updates multiply by `dt * 60` so they are normalized to "per frame at 60 fps":
```js
entity.x += vx * dt * 60;
```
`dt` is capped at `0.1s` in the loop to prevent spiral-of-death on tab focus.

### Mouse Coordinate Conversion
Always convert mouse events to canvas space (handles CSS scaling):
```js
const r = canvas.getBoundingClientRect();
mouse.x = (e.clientX - r.left) * (W / r.width);
mouse.y = (e.clientY - r.top)  * (H / r.height);
```

### Color Palette
All colors are defined in the `PAL` object (Section 1). Add new colors there rather than using inline hex strings. The retro palette is dark navy background (`#111122`) with neon green player, yellow bullets, red/orange/purple enemies.

### Adding a New Enemy Type
1. Add a key to the `ENEMY` constant object
2. Add stats to `ENEMY_BASE`
3. Write a `drawEnemyX(ctx, e)` function in Section 9
4. Wire it into `drawEnemies()` dispatch
5. Add it to `waves` arrays in `DEFINED_LEVELS` or `getLevelConfig`

### localStorage
`pixelAssaultHi` — hi-score for Pixel Assault (persisted across sessions).
