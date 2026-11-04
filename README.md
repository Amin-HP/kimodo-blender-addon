# Kimodo Motion Importer for Blender

Bring motions generated with [**Kimodo**](https://github.com/nv-tlabs/kimodo) into Blender and put them
on **your own rigged character**, whether it comes from Mixamo, Rigify, an Unreal mannequin, VRM,
Character Creator, or a hand-made rig.

![Kimodo motion (left, black skeleton) retargeted onto an A-pose character rig (right)](images/demo.gif)

*Left: the raw Kimodo skeleton. Right: the same motion retargeted onto a different rig. That rig
has different proportions, an A-pose rest pose and Mixamo bone names.*

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Download](#download)
- [Installation](#installation)
- [Quick start](#quick-start)
- [The Kimodo panel](#the-kimodo-panel)
- [Bone mapping](#bone-mapping)
- [Options](#options)
- [Supported Kimodo skeletons](#supported-kimodo-skeletons)
- [Tips and troubleshooting](#tips-and-troubleshooting)
- [How it works](#how-it-works)
- [Building the zip from source](#building-the-zip-from-source)
- [Credits and license](#credits-and-license)

---

## Features

- **One-click import** of Kimodo `.npz` motions as an animated Kimodo skeleton, for a quick preview.
- **Retargeting onto any humanoid rig**, baked into a normal Blender action that you can edit, put
  in the NLA, or export to FBX/glTF.
- **Automatic bone mapping** for common naming conventions: Mixamo, Unreal (UE4/UE5), Rigify
  `DEF-`, VRM, Character Creator, 3ds Max Biped, SMPL and Kimodo's own names.
- **Works with A-pose and T-pose rigs**: limb rest directions are aligned automatically.
- **Handles any facing direction and object transform**: FBX imports with 90° rotation and 0.01
  scale work as-is.
- **Root motion scaled to your character's size** so the feet don't slide; an *In place* option
  removes forward travel.
- **No extra installs**: uses only Python and numpy, which ship with Blender.

## Requirements

| | |
| --- | --- |
| Blender | **4.2 or newer** (installs as an extension); 3.6 – 4.1 work as a legacy add-on. Tested on Blender 5.2. |
| Input | A Kimodo motion exported in the **NPZ** format (see [Quick start](#quick-start)). |
| Character | A rigged (armature) character, preferably humanoid. |

## Download

Download **[`kimodo_npz_importer.zip`](../../releases/latest/download/kimodo_npz_importer.zip)** from
the [latest release](../../releases/latest).

> Do **not** unzip it. Blender installs the zip file directly.

## Installation

### Blender 4.2 and newer

1. Open **Edit → Preferences → Get Extensions**.
2. Click the **⌄** menu in the top-right corner, then **Install from Disk...**
3. Select `kimodo_npz_importer.zip`. The add-on is enabled automatically.

You can also **drag and drop** the zip file into the Blender window.

### Blender 3.6 – 4.1

1. Open **Edit → Preferences → Add-ons → Install...**
2. Select `kimodo_npz_importer.zip`.
3. Tick the checkbox next to **Animation: Kimodo Motion Importer (.npz)**.

After installing, the **Kimodo** tab appears in the 3D Viewport sidebar (press **N**). There is
also a new menu entry, **File → Import → Kimodo Motion (.npz)**.

## Quick start

### 1. Export the motion from Kimodo

In the Kimodo interactive demo, generate a motion, then open **Exports → Motion**, choose the
**NPZ** format and download it.
(The CLI writes the same format: `kimodo_gen ... --output my_motion`.)

> For SMPL-X models choose **NPZ**, not **AMASS NPZ**.

### 2. Import it into Blender

1. Open your character's `.blend` file, or import your character (FBX, glTF, ...).
2. Press **N** in the 3D Viewport and open the **Kimodo** tab.
3. Click the folder icon and pick your `.npz` file.
4. Set **FPS** to the frame rate of the Kimodo model. The demo shows it as *Model FPS*; it is
   usually **30**.

### 3. Put the motion on your character

1. **Target rig**: pick your character's **armature** object (not the mesh).
2. Click **Auto-map Bones**, then check the bone map list (see [Bone mapping](#bone-mapping)).
3. Click **Apply Motion to Rig**.
4. Press **Space** to play. 🎉

The motion is baked into a new action named `Kimodo_<file>_<rig>`. Your mesh follows through its
Armature modifier, so no extra setup is needed.

> **Just want to look at the raw motion?** Click **Import as Kimodo Skeleton**. This creates an
> animated stick-figure armature named `Kimodo_<file>`.

## The Kimodo panel

![The Kimodo panel in the 3D Viewport sidebar](images/ui_overview.png)

| Control | What it does |
| --- | --- |
| **NPZ file** | The Kimodo motion to load. |
| **FPS** | Frame rate of the motion (Kimodo models usually run at 30 FPS). |
| **Start** | First frame of the baked animation. |
| **Set scene FPS / range** | Also sets the scene frame rate and frame range to match the motion. |
| **Import as Kimodo Skeleton** | Creates a new armature with Kimodo's own skeleton and animates it. |
| **Target rig** | The armature that should receive the motion. |
| **Auto-map Bones** | Detects the Kimodo skeleton type from the file and guesses the bone mapping. |
| **✕** (next to Auto-map) | Clears all target bones from the mapping. |
| **Bone map** | One row per Kimodo joint → your bone. Click a row's field to choose another bone. |
| **Show unmapped joints** | Also lists Kimodo joints that are not mapped yet (fingers, eyes, ...). |
| **Rest pose / Current pose** | Which pose of your rig matches Kimodo's T-pose (see [Options](#options)). |
| **Auto-align limbs**, **Auto-detect facing**, **Scale root motion**, **In place** | See [Options](#options). |
| **Apply Motion to Rig** | Retargets and bakes the motion onto the target rig. |

## Bone mapping

Kimodo drives about 22 body joints: hips, spine, neck, head, shoulders, arms, forearms, hands,
thighs, shins, feet and toes. **Auto-map Bones** recognises these naming styles:

| Rig type | Example bone names |
| --- | --- |
| Mixamo | `mixamorig:Hips`, `mixamorig:LeftArm`, `mixamorig:RightUpLeg` |
| Unreal (UE4 / UE5) | `pelvis`, `upperarm_l`, `lowerarm_r`, `thigh_l`, `calf_r`, `ball_l` |
| Rigify (deform bones) | `DEF-upper_arm.L`, `DEF-forearm.R`, `DEF-thigh.L`, `DEF-shin.R` |
| VRM / VRoid | `J_Bip_C_Hips`, `J_Bip_L_UpperArm`, `J_Bip_R_LowerLeg` |
| Character Creator | `CC_Base_L_Upperarm`, `CC_Base_R_Thigh` |
| 3ds Max Biped | `Bip01 L Thigh`, `Bip01 R Forearm` |
| SMPL / SMPL-X | `pelvis`, `left_hip`, `left_knee`, `left_collar` |
| Kimodo / SOMA | `Hips`, `LeftArm`, `LeftShin`, ... (exact name match) |

Twist, IK, pole and helper bones (for example `upperarm_twist_01_l`, `MCH-thigh_ik.L`, `ORG-*`)
are ignored. Spine bones are found by walking the hierarchy between the hips and the neck, so
rigs with 1–5 spine bones all work.

**Fixing a wrong or missing bone:** click the bone field in that row and pick the right bone
from the list. Clear a row with its **✕** button.

**Fingers** (SOMA 77-joint motions only) are not mapped automatically. Enable **Show unmapped
joints** and map them by hand if your rig has fingers.

The mapping is saved in the `.blend` file. Applying a second motion with the same skeleton
reuses it.

## Options

| Option | Default | When to change it |
| --- | --- | --- |
| **Rest pose** / **Current pose** | Rest pose | *Rest pose* treats your rig's rest pose as Kimodo's T-pose and works for most rigs. If your rig's rest pose is unusual (e.g. arms forward), choose *Current pose*. Then pose the rig into a T-pose facing the same way as the character, and click Apply. |
| **Auto-align limbs** | On | Compensates for differences between your rig's arm and leg directions and Kimodo's T-pose, so **A-pose** rigs work. Turn it off if your rig is already in an exact T-pose and you see small wrist or shoulder twists. |
| **Auto-detect facing** | On | Works out which way the character faces from its left/right hips (or shoulders). Turn it off only if your left/right bones are mislabelled. |
| **Scale root motion** | On | Scales hip translation by *your hip height / Kimodo hip height*, so a small character takes smaller steps. Turn it off to keep the exact distances in meters. |
| **In place** | Off | Removes horizontal hip translation, so the character stays on the spot. Useful for game loops. |

## Supported Kimodo skeletons

The skeleton is detected automatically from the number of joints in the file.

| Kimodo model | Skeleton | Joints | Notes |
| --- | --- | --- | --- |
| Kimodo-SOMA | `somaskel77` | 77 | Default demo export; includes fingers. |
| Kimodo-SOMA (older files) | `somaskel30` | 30 | Compact skeleton without fingers. |
| Kimodo-SMPLX | `smplx22` | 22 | Body only. Export as **NPZ**, not AMASS NPZ. |
| Kimodo-G1 | `g1skel34` | 34 | Unitree G1 robot. Its zero pose has the arms down; *Auto-align limbs* compensates. |

## Tips and troubleshooting

**The character doesn't move / "No bones are mapped".**
Make sure **Target rig** is the *armature* object, not the mesh. Then click **Auto-map Bones** and
check that at least the hips are mapped.

**Arms or legs are twisted or point the wrong way.**
- Check the mapping. A common mix-up is *UpLeg* (thigh) vs *Leg* (shin) in Mixamo naming.
- Try **Current pose** mode: pose the rig into a clean T-pose first, then Apply.
- If your rig is in an exact T-pose, try turning **Auto-align limbs** off.

**The character slides or floats.**
Keep **Scale root motion** on. The add-on measures your hip height from the lowest bone, so make
sure the rig's feet touch the floor in its rest pose.

**I use Rigify.**
Retarget onto the **metarig** or onto the **`DEF-` bones**, not onto the control rig, which
contains IK and FK controls. You can then bake the result onto the controls with Rigify's
tools if needed.

**The animation plays too fast or too slow.**
Set **FPS** to the Kimodo model's frame rate (usually 30) and keep **Set scene FPS / range** on.

**"This looks like an AMASS NPZ".**
Export the motion with the plain **NPZ** format instead.

**Exporting to a game engine.**
The result is a regular Blender action on your armature. Export with **File → Export → FBX** or
**glTF** as usual, with *Bake Animation* enabled.

**Applying a new motion.**
Each Apply creates a new action. Older actions stay in the file and can be chosen in the
Action Editor or Dope Sheet, or combined in the NLA editor.

## How it works

A Kimodo NPZ stores, per frame, the **global rotation** of every joint (`global_rot_mats`) and its
world position (`posed_joints`). These rotations are measured relative to Kimodo's rest pose: a
T-pose standing on the floor, Y-up, facing +Z.

The add-on:

1. Converts the motion from Kimodo's Y-up space to Blender's Z-up space (the character faces −Y).
2. For each mapped bone, applies the same **world-space rotation change** that the Kimodo joint has
   from its T-pose to your bone's reference pose. Limb bones first get a small alignment
   rotation, so A-pose arms line up with Kimodo's T-pose arms.
3. Moves the hips along the Kimodo root trajectory, scaled by the hip-height ratio and rotated to
   the direction your character faces.
4. Converts everything back to each bone's local space and writes all keyframes directly into a
   new action. This is fast even for long clips.

Because only world-space rotations are transferred, the result does not depend on bone rolls,
bone lengths or how the bones are parented.

## Building the zip from source

```bash
python build_zip.py      # writes dist/kimodo_npz_importer.zip
```

Repository layout:

```
kimodo_npz_importer/
    __init__.py              # the add-on
    blender_manifest.toml    # Blender 4.2+ extension manifest
images/                      # README images
build_zip.py                 # packs the installable zip
```

## Credits and license

- Add-on by **AminHP**.
- [Kimodo](https://github.com/nv-tlabs/kimodo) by NVIDIA. The skeleton definitions embedded in
  this add-on come from Kimodo's assets (Apache-2.0).
- Licensed under the [Apache License 2.0](LICENSE).
