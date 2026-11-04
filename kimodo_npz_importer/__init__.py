# SPDX-FileCopyrightText: Copyright (c) 2026 AminHP
# SPDX-License-Identifier: Apache-2.0
"""Blender add-on: import Kimodo ``.npz`` motions and retarget them onto rigged characters.

Install: Edit > Preferences > Add-ons > (v) menu > Install from Disk... > pick this file.
Use:     3D Viewport > Sidebar (N) > "Kimodo" tab, or File > Import > Kimodo Motion (.npz).

The add-on is self-contained (only numpy, which ships with Blender). It reads the
``global_rot_mats`` / ``posed_joints`` arrays written by the Kimodo demo "NPZ" export
(or ``local_rot_mats`` + ``root_positions`` if those are the only arrays present).

Retargeting works in world space: Kimodo global rotations are relative to the Kimodo rest
pose (a T-pose facing +Z, Y-up). For every mapped bone the target bone receives the same
world-space rotation delta on top of its own reference pose (rest pose or current pose).
Limb bones are additionally aligned so A-pose rigs work without manual posing.
"""

bl_info = {
    "name": "Kimodo Motion Importer (.npz)",
    "author": "AminHP",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Kimodo, File > Import > Kimodo Motion (.npz)",
    "description": "Import Kimodo NPZ motions and retarget them onto rigged characters",
    "doc_url": "https://github.com/Amin-HP/kimodo-blender-addon",
    "category": "Animation",
}

import math
import os
import re

import bpy
import numpy as np
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, UIList
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix, Vector

# ----------------------------------------------------------------------------------------
# Skeleton definitions (joint name, parent index, rest position in meters, Y-up, facing +Z)
# Generated from kimodo.skeleton.registry.build_skeleton(n).neutral_joints
# ----------------------------------------------------------------------------------------

SKELETONS = {
    77: ("somaskel77", [
        ("Hips", -1, (0.0, 0.0, 0.0)),
        ("Spine1", 0, (-0.00014, 0.05004, -0.00054)),
        ("Spine2", 1, (-0.00014, 0.12129, -0.00084)),
        ("Chest", 2, (-0.00014, 0.19679, -0.009)),
        ("Neck1", 3, (-0.00195, 0.4599, -0.01453)),
        ("Neck2", 4, (-0.00195, 0.537, 0.0085)),
        ("Head", 5, (-0.00195, 0.59829, 0.02803)),
        ("HeadEnd", 6, (-0.00192, 0.75894, 0.00968)),
        ("Jaw", 6, (-0.00193, 0.60304, 0.05898)),
        ("LeftEye", 6, (0.03011, 0.65209, 0.1039)),
        ("RightEye", 6, (-0.03418, 0.65191, 0.10362)),
        ("LeftShoulder", 3, (0.01608, 0.42916, 0.04214)),
        ("LeftArm", 11, (0.16528, 0.42916, -0.01288)),
        ("LeftForeArm", 12, (0.45267, 0.42916, -0.01291)),
        ("LeftHand", 13, (0.72361, 0.42916, -0.01288)),
        ("LeftHandThumb1", 14, (0.74638, 0.41524, 0.01903)),
        ("LeftHandThumb2", 15, (0.7865, 0.39696, 0.03545)),
        ("LeftHandThumb3", 16, (0.81449, 0.39696, 0.03545)),
        ("LeftHandThumbEnd", 17, (0.8463, 0.39696, 0.03545)),
        ("LeftHandIndex1", 14, (0.75609, 0.42384, 0.01008)),
        ("LeftHandIndex2", 19, (0.81973, 0.42396, 0.01186)),
        ("LeftHandIndex3", 20, (0.85636, 0.42396, 0.01186)),
        ("LeftHandIndex4", 21, (0.87965, 0.42396, 0.01186)),
        ("LeftHandIndexEnd", 22, (0.90724, 0.42216, 0.01073)),
        ("LeftHandMiddle1", 14, (0.75525, 0.43157, -0.00288)),
        ("LeftHandMiddle2", 24, (0.81715, 0.42898, -0.01291)),
        ("LeftHandMiddle3", 25, (0.86072, 0.42898, -0.01291)),
        ("LeftHandMiddle4", 26, (0.89069, 0.42898, -0.01291)),
        ("LeftHandMiddleEnd", 27, (0.91373, 0.42603, -0.01322)),
        ("LeftHandRing1", 14, (0.75244, 0.42863, -0.01611)),
        ("LeftHandRing2", 29, (0.81098, 0.42376, -0.02985)),
        ("LeftHandRing3", 30, (0.85449, 0.42376, -0.02985)),
        ("LeftHandRing4", 31, (0.881, 0.42376, -0.02985)),
        ("LeftHandRingEnd", 32, (0.90036, 0.42454, -0.02985)),
        ("LeftHandPinky1", 14, (0.75227, 0.42606, -0.02889)),
        ("LeftHandPinky2", 34, (0.80314, 0.41275, -0.0466)),
        ("LeftHandPinky3", 35, (0.83385, 0.41275, -0.0466)),
        ("LeftHandPinky4", 36, (0.84935, 0.41275, -0.0466)),
        ("LeftHandPinkyEnd", 37, (0.8688, 0.41117, -0.04603)),
        ("RightShoulder", 3, (-0.01394, 0.42859, 0.04315)),
        ("RightArm", 39, (-0.16431, 0.42859, -0.01231)),
        ("RightForeArm", 40, (-0.45168, 0.42859, -0.01234)),
        ("RightHand", 41, (-0.72301, 0.42859, -0.01231)),
        ("RightHandThumb1", 42, (-0.74575, 0.41475, 0.01932)),
        ("RightHandThumb2", 43, (-0.78587, 0.39648, 0.03573)),
        ("RightHandThumb3", 44, (-0.81382, 0.39648, 0.03573)),
        ("RightHandThumbEnd", 45, (-0.84566, 0.39648, 0.03573)),
        ("RightHandIndex1", 42, (-0.75555, 0.42339, 0.01052)),
        ("RightHandIndex2", 47, (-0.81896, 0.42352, 0.0123)),
        ("RightHandIndex3", 48, (-0.85551, 0.42352, 0.0123)),
        ("RightHandIndex4", 49, (-0.87879, 0.42352, 0.0123)),
        ("RightHandIndexEnd", 50, (-0.90641, 0.42171, 0.01117)),
        ("RightHandMiddle1", 42, (-0.75469, 0.43106, -0.0023)),
        ("RightHandMiddle2", 52, (-0.8165, 0.42847, -0.01231)),
        ("RightHandMiddle3", 53, (-0.85999, 0.42847, -0.01231)),
        ("RightHandMiddle4", 54, (-0.88999, 0.42847, -0.01231)),
        ("RightHandMiddleEnd", 55, (-0.91302, 0.42553, -0.01263)),
        ("RightHandRing1", 42, (-0.75187, 0.42791, -0.0154)),
        ("RightHandRing2", 57, (-0.81041, 0.42305, -0.02914)),
        ("RightHandRing3", 58, (-0.8538, 0.42305, -0.02914)),
        ("RightHandRing4", 59, (-0.88035, 0.42305, -0.02914)),
        ("RightHandRingEnd", 60, (-0.89968, 0.42383, -0.02914)),
        ("RightHandPinky1", 42, (-0.75168, 0.42517, -0.02815)),
        ("RightHandPinky2", 62, (-0.80259, 0.41185, -0.04587)),
        ("RightHandPinky3", 63, (-0.83322, 0.41185, -0.04587)),
        ("RightHandPinky4", 64, (-0.84868, 0.41185, -0.04587)),
        ("RightHandPinkyEnd", 65, (-0.86813, 0.41027, -0.0453)),
        ("LeftLeg", 0, (0.10043, -0.08435, 0.02596)),
        ("LeftShin", 67, (0.10043, -0.51656, 0.01793)),
        ("LeftFoot", 68, (0.10043, -0.93811, -0.01689)),
        ("LeftToeBase", 69, (0.10043, -0.98871, 0.11543)),
        ("LeftToeEnd", 70, (0.10034, -1.00518, 0.18056)),
        ("RightLeg", 0, (-0.10047, -0.08295, 0.0262)),
        ("RightShin", 72, (-0.10047, -0.51657, 0.01815)),
        ("RightFoot", 73, (-0.10047, -0.93775, -0.01664)),
        ("RightToeBase", 74, (-0.10047, -0.98854, 0.11621)),
        ("RightToeEnd", 75, (-0.10038, -1.00489, 0.18081)),
    ]),
    30: ("somaskel30", [
        ("Hips", -1, (0.0, 0.0, 0.0)),
        ("Spine1", 0, (-0.00014, 0.05004, -0.00054)),
        ("Spine2", 1, (-0.00014, 0.12129, -0.00084)),
        ("Chest", 2, (-0.00014, 0.19679, -0.009)),
        ("Neck1", 3, (-0.00195, 0.4599, -0.01453)),
        ("Neck2", 4, (-0.00195, 0.537, 0.0085)),
        ("Head", 5, (-0.00195, 0.59829, 0.02803)),
        ("Jaw", 6, (-0.00193, 0.60304, 0.05898)),
        ("LeftEye", 6, (0.03011, 0.65209, 0.1039)),
        ("RightEye", 6, (-0.03418, 0.65191, 0.10362)),
        ("LeftShoulder", 3, (0.01608, 0.42916, 0.04214)),
        ("LeftArm", 10, (0.16528, 0.42916, -0.01288)),
        ("LeftForeArm", 11, (0.45267, 0.42916, -0.01291)),
        ("LeftHand", 12, (0.72361, 0.42916, -0.01288)),
        ("LeftHandThumbEnd", 13, (0.8463, 0.39696, 0.03545)),
        ("LeftHandMiddleEnd", 13, (0.91373, 0.42603, -0.01322)),
        ("RightShoulder", 3, (-0.01394, 0.42859, 0.04315)),
        ("RightArm", 16, (-0.16431, 0.42859, -0.01231)),
        ("RightForeArm", 17, (-0.45168, 0.42859, -0.01234)),
        ("RightHand", 18, (-0.72301, 0.42859, -0.01231)),
        ("RightHandThumbEnd", 19, (-0.84566, 0.39648, 0.03573)),
        ("RightHandMiddleEnd", 19, (-0.91302, 0.42553, -0.01263)),
        ("LeftLeg", 0, (0.10043, -0.08435, 0.02596)),
        ("LeftShin", 22, (0.10043, -0.51656, 0.01793)),
        ("LeftFoot", 23, (0.10043, -0.93811, -0.01689)),
        ("LeftToeBase", 24, (0.10043, -0.98871, 0.11543)),
        ("RightLeg", 0, (-0.10047, -0.08295, 0.0262)),
        ("RightShin", 26, (-0.10047, -0.51657, 0.01815)),
        ("RightFoot", 27, (-0.10047, -0.93775, -0.01664)),
        ("RightToeBase", 28, (-0.10047, -0.98854, 0.11621)),
    ]),
    22: ("smplx22", [
        ("pelvis", -1, (0.00225, -0.37226, 0.01233)),
        ("left_hip", 0, (0.05455, -0.4662, -0.01528)),
        ("right_hip", 0, (-0.05494, -0.47881, -0.00989)),
        ("spine1", 0, (0.00076, -0.25933, -0.01265)),
        ("left_knee", 1, (0.11342, -0.88264, -0.02183)),
        ("right_knee", 2, (-0.10301, -0.87637, -0.02395)),
        ("spine2", 3, (0.00766, -0.1137, -0.01951)),
        ("left_ankle", 4, (0.07168, -1.32022, -0.05135)),
        ("right_ankle", 5, (-0.08853, -1.32322, -0.04198)),
        ("spine3", 6, (-0.00268, -0.05761, 0.00161)),
        ("left_foot", 7, (0.12097, -1.3855, 0.07491)),
        ("right_foot", 8, (-0.1291, -1.38851, 0.0851)),
        ("neck", 9, (-0.0137, 0.11375, -0.02722)),
        ("left_collar", 9, (0.04505, 0.03003, -0.00677)),
        ("right_collar", 9, (-0.04931, 0.029, -0.01326)),
        ("head", 12, (0.01095, 0.28914, -0.00276)),
        ("left_shoulder", 13, (0.17133, 0.08771, -0.02066)),
        ("right_shoulder", 14, (-0.15865, 0.08267, -0.02238)),
        ("left_elbow", 16, (0.44424, 0.01786, -0.05975)),
        ("right_elbow", 17, (-0.45068, 0.04723, -0.04694)),
        ("left_wrist", 18, (0.72041, 0.03911, -0.06223)),
        ("right_wrist", 19, (-0.72256, 0.0424, -0.06339)),
    ]),
    34: ("g1skel34", [
        ("pelvis_skel", -1, (0.0, 0.0, 0.0)),
        ("left_hip_pitch_skel", 0, (0.06445, -0.1027, -0.0)),
        ("left_hip_roll_skel", 1, (0.11645, -0.13316, -0.0)),
        ("left_hip_yaw_skel", 2, (0.11645, -0.25728, 0.025)),
        ("left_knee_skel", 3, (0.1186, -0.43462, -0.05327)),
        ("left_ankle_pitch_skel", 4, (0.11851, -0.73464, -0.05327)),
        ("left_ankle_roll_skel", 5, (0.11851, -0.75219, -0.05327)),
        ("left_toe_base", 6, (0.11851, -0.78719, 0.08673)),
        ("right_hip_pitch_skel", 0, (-0.06445, -0.1027, -0.0)),
        ("right_hip_roll_skel", 8, (-0.11645, -0.13316, -0.0)),
        ("right_hip_yaw_skel", 9, (-0.11645, -0.25728, 0.025)),
        ("right_knee_skel", 10, (-0.1186, -0.43462, -0.05327)),
        ("right_ankle_pitch_skel", 11, (-0.11851, -0.73464, -0.05327)),
        ("right_ankle_roll_skel", 12, (-0.11851, -0.75219, -0.05327)),
        ("right_toe_base", 13, (-0.11851, -0.78719, 0.08673)),
        ("waist_yaw_skel", 0, (0.0, 0.0, 0.0)),
        ("waist_roll_skel", 15, (-0.0, 0.044, -0.00396)),
        ("waist_pitch_skel", 16, (-0.0, 0.044, -0.00396)),
        ("left_shoulder_pitch_skel", 17, (0.10022, 0.29178, -1e-05)),
        ("left_shoulder_roll_skel", 18, (0.13822, 0.27795, -1e-05)),
        ("left_shoulder_yaw_skel", 19, (0.14446, 0.17475, -1e-05)),
        ("left_elbow_skel", 20, (0.14446, 0.09423, 0.01578)),
        ("left_wrist_roll_skel", 21, (0.14635, 0.08423, 0.11578)),
        ("left_wrist_pitch_skel", 22, (0.14635, 0.08423, 0.15378)),
        ("left_wrist_yaw_skel", 23, (0.14635, 0.08423, 0.19978)),
        ("left_hand_roll_skel", 24, (0.14635, 0.08423, 0.29978)),
        ("right_shoulder_pitch_skel", 17, (-0.10021, 0.29178, -1e-05)),
        ("right_shoulder_roll_skel", 26, (-0.13821, 0.27795, -1e-05)),
        ("right_shoulder_yaw_skel", 27, (-0.14445, 0.17475, -1e-05)),
        ("right_elbow_skel", 28, (-0.14445, 0.09423, 0.01578)),
        ("right_wrist_roll_skel", 29, (-0.14634, 0.08423, 0.11578)),
        ("right_wrist_pitch_skel", 30, (-0.14634, 0.08423, 0.15378)),
        ("right_wrist_yaw_skel", 31, (-0.14634, 0.08423, 0.19978)),
        ("right_hand_roll_skel", 32, (-0.14634, 0.08423, 0.29978)),
    ]),
}

# Semantic body parts -> source joint names, per skeleton. Used by auto-mapping.
_SOMA_CANON = {
    "hips": "Hips",
    "neck": "Neck1",
    "head": "Head",
    "spine": ["Spine1", "Spine2", "Chest"],
}
for _s, _S in (("L", "Left"), ("R", "Right")):
    _SOMA_CANON.update(
        {
            f"shoulder.{_s}": f"{_S}Shoulder",
            f"upperarm.{_s}": f"{_S}Arm",
            f"forearm.{_s}": f"{_S}ForeArm",
            f"hand.{_s}": f"{_S}Hand",
            f"thigh.{_s}": f"{_S}Leg",
            f"shin.{_s}": f"{_S}Shin",
            f"foot.{_s}": f"{_S}Foot",
            f"toe.{_s}": f"{_S}ToeBase",
        }
    )

_SMPLX_CANON = {"hips": "pelvis", "neck": "neck", "head": "head", "spine": ["spine1", "spine2", "spine3"]}
for _s, _S in (("L", "left"), ("R", "right")):
    _SMPLX_CANON.update(
        {
            f"shoulder.{_s}": f"{_S}_collar",
            f"upperarm.{_s}": f"{_S}_shoulder",
            f"forearm.{_s}": f"{_S}_elbow",
            f"hand.{_s}": f"{_S}_wrist",
            f"thigh.{_s}": f"{_S}_hip",
            f"shin.{_s}": f"{_S}_knee",
            f"foot.{_s}": f"{_S}_ankle",
            f"toe.{_s}": f"{_S}_foot",
        }
    )

_G1_CANON = {"hips": "pelvis_skel", "spine": ["waist_pitch_skel"]}
for _s, _S in (("L", "left"), ("R", "right")):
    _G1_CANON.update(
        {
            f"upperarm.{_s}": f"{_S}_shoulder_yaw_skel",
            f"forearm.{_s}": f"{_S}_elbow_skel",
            f"hand.{_s}": f"{_S}_wrist_yaw_skel",
            f"thigh.{_s}": f"{_S}_hip_yaw_skel",
            f"shin.{_s}": f"{_S}_knee_skel",
            f"foot.{_s}": f"{_S}_ankle_roll_skel",
        }
    )

CANON = {"somaskel77": _SOMA_CANON, "somaskel30": _SOMA_CANON, "smplx22": _SMPLX_CANON, "g1skel34": _G1_CANON}

# Limb parts whose rest direction is aligned between source and target (fixes A-pose vs T-pose).
ALIGN_PARTS = ("shoulder", "upperarm", "forearm", "hand", "thigh", "shin")

# Kimodo (Y-up, facing +Z, left = +X)  ->  Blender (Z-up, facing -Y, left = +X)
C_YUP_TO_ZUP = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])


# ----------------------------------------------------------------------------------------
# Motion loading
# ----------------------------------------------------------------------------------------


class KimodoMotion:
    """Kimodo motion converted to Blender space (Z-up)."""

    def __init__(self, path):
        with np.load(path, allow_pickle=False) as data:
            arrays = {k: np.asarray(data[k]) for k in data.files}

        if "global_rot_mats" not in arrays and "local_rot_mats" not in arrays:
            if "pose_body" in arrays or "trans" in arrays:
                raise ValueError(
                    "This looks like an AMASS NPZ. Export the motion with the 'NPZ' format "
                    "(Kimodo NPZ) instead of 'AMASS NPZ'."
                )
            raise ValueError(f"Not a Kimodo NPZ (keys: {sorted(arrays)})")

        def unbatch(a, ndim):
            a = np.asarray(a, dtype=np.float64)
            while a.ndim > ndim:
                a = a[0]
            return a

        if "global_rot_mats" in arrays:
            G = unbatch(arrays["global_rot_mats"], 4)
        else:
            G = None
        L = unbatch(arrays["local_rot_mats"], 4) if "local_rot_mats" in arrays else None

        J = (G if G is not None else L).shape[1]
        if J not in SKELETONS:
            raise ValueError(f"Unsupported joint count {J}; expected one of {sorted(SKELETONS)}")
        self.skeleton_name, joints = SKELETONS[J]
        self.names = [j[0] for j in joints]
        self.parents = [j[1] for j in joints]
        rest = np.array([j[2] for j in joints], dtype=np.float64)
        self.root = self.parents.index(-1)

        if "posed_joints" in arrays:
            P = unbatch(arrays["posed_joints"], 3)
        else:
            P = None

        if G is None or P is None:
            if L is None or "root_positions" not in arrays:
                raise ValueError("NPZ needs global_rot_mats + posed_joints, or local_rot_mats + root_positions")
            G, P = self._fk(L, unbatch(arrays["root_positions"], 2), rest)

        C = C_YUP_TO_ZUP
        self.G = np.einsum("ij,tkjl,ml->tkim", C, G, C)  # C @ G @ C^T
        self.P = P @ C.T
        self.rest = rest @ C.T
        self.num_frames = self.G.shape[0]
        self.children = [[] for _ in self.names]
        for j, p in enumerate(self.parents):
            if p >= 0:
                self.children[p].append(j)

    def _fk(self, L, root_pos, rest):
        T, J = L.shape[:2]
        G = np.empty_like(L)
        P = np.empty((T, J, 3))
        for j in range(J):
            p = self.parents[j]
            if p < 0:
                G[:, j] = L[:, j]
                P[:, j] = root_pos
            else:
                G[:, j] = G[:, p] @ L[:, j]
                P[:, j] = P[:, p] + np.einsum("tij,j->ti", G[:, p], rest[j] - rest[p])
        return G, P

    def index(self, name):
        return self.names.index(name)

    def main_child(self, j):
        kids = self.children[j]
        if not kids:
            return None
        if len(kids) == 1:
            return kids[0]
        for key in ("Middle", "Spine", "spine", "waist", "Neck", "neck", "Head", "head", "ToeBase", "foot"):
            for k in kids:
                if key in self.names[k]:
                    return k
        return kids[0]

    def rest_direction(self, j):
        c = self.main_child(j)
        if c is None:
            return None
        d = Vector(self.rest[c] - self.rest[j])
        return d.normalized() if d.length > 1e-6 else None

    def rest_hip_height(self):
        return float(self.rest[self.root, 2] - self.rest[:, 2].min())


# ----------------------------------------------------------------------------------------
# Auto-mapping of target bones
# ----------------------------------------------------------------------------------------

_EXCLUDE_TOKENS = {
    "ik", "fk", "mch", "org", "pole", "target", "twist", "roll", "end", "nub", "tip", "helper",
    "ctrl", "ctl", "tweak", "vis", "parent", "socket", "prop", "attach", "ref", "ik_target",
}
_NOISE_TOKENS = {"def", "bip", "bip01", "bip001", "j", "jnt", "joint", "cc", "base", "bone", "b", "c", "sk"}
_SIDE_TOKENS = {"l": "L", "left": "L", "r": "R", "right": "R"}

_ALIASES = {
    "hips": {"hips", "pelvis"},
    "neck": {"neck", "neck1", "neck01"},
    "head": {"head"},
    "shoulder": {"shoulder", "clavicle", "collar", "clav", "collarbone"},
    "upperarm": {"arm", "upperarm", "uparm"},
    "forearm": {"forearm", "lowerarm", "elbow", "lowarm"},
    "hand": {"hand", "wrist"},
    "thigh": {"upleg", "thigh", "upperleg", "hip"},
    "shin": {"leg", "calf", "shin", "lowerleg", "knee", "lowleg"},
    "foot": {"foot", "ankle"},
    "toe": {"toebase", "toe", "toes", "ball", "toe0"},
}
_UNSIDED_PARTS = {"hips", "neck", "head"}


def _tokens(name):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t]


def _parse_bone_name(name):
    toks = _tokens(name)
    if any(t in _EXCLUDE_TOKENS for t in toks):
        return None, None
    side = None
    rest = []
    for t in toks:
        if re.fullmatch(r"mixamorig\d*", t) or t in _NOISE_TOKENS:
            continue
        if t in _SIDE_TOKENS and side is None:
            side = _SIDE_TOKENS[t]
            continue
        rest.append(t)
    return "".join(rest), side


def _bone_depth(bone):
    d = 0
    while bone.parent:
        bone = bone.parent
        d += 1
    return d


def auto_map(arm_obj, motion):
    """Return {source_joint_name: target_bone_name}."""
    bones = arm_obj.data.bones
    canon = CANON[motion.skeleton_name]
    src_norm = {re.sub(r"[^a-z0-9]", "", n.lower()): n for n in motion.names}
    mapping = {}

    # 1) exact name matches (rigs that already use Kimodo joint names, e.g. SOMA BVH imports)
    for b in bones:
        key = re.sub(r"[^a-z0-9]", "", b.name.lower())
        if key in src_norm and src_norm[key] not in mapping:
            mapping[src_norm[key]] = b.name
    if len(mapping) >= len(canon) - 1:
        return mapping

    # 2) semantic matching by common naming conventions (Mixamo, UE, Rigify DEF, VRM, CC, ...)
    parsed = {b.name: _parse_bone_name(b.name) for b in bones}
    bases = {base for base, _ in parsed.values() if base}
    smpl_like_shoulder = bool(bases & {"collar", "clavicle"})
    smpl_like_foot = "ankle" in bases

    candidates = {}
    for b in bones:
        base, side = parsed[b.name]
        if not base:
            continue
        for part, aliases in _ALIASES.items():
            if base not in aliases:
                continue
            if part == "shoulder" and base == "shoulder" and smpl_like_shoulder:
                part = "upperarm"
            if part == "foot" and base == "foot" and smpl_like_foot:
                part = "toe"
            if part == "thigh" and base == "hip" and side is None:
                part = "hips"
            if part in _UNSIDED_PARTS:
                key = part
            elif side:
                key = f"{part}.{side}"
            else:
                continue
            candidates.setdefault(key, []).append((_bone_depth(b), b.name))

    found = {k: min(v)[1] for k, v in candidates.items()}
    for key, tgt in found.items():
        src = canon.get(key)
        if isinstance(src, str):
            mapping.setdefault(src, tgt)

    # 3) spine: walk the hierarchy between hips and neck/head/shoulder
    hips = found.get("hips")
    top = found.get("neck") or found.get("head") or found.get("shoulder.L") or found.get("upperarm.L")
    if hips and top:
        chain = []
        b = bones[top].parent
        while b is not None and b.name != hips:
            chain.append(b.name)
            b = b.parent
        if b is not None:  # reached hips
            chain.reverse()
            src_spine = canon.get("spine", [])
            n, m = len(chain), len(src_spine)
            if n and m:
                mapping.setdefault(src_spine[-1], chain[-1])
                if n > 1 and m > 1:
                    mapping.setdefault(src_spine[0], chain[0])
                if n > 2 and m > 2:
                    mapping.setdefault(src_spine[m // 2], chain[n // 2])
    return mapping


# ----------------------------------------------------------------------------------------
# Retargeting core
# ----------------------------------------------------------------------------------------


def _m3(a):
    return Matrix([list(r) for r in a])


def _np3(m):
    return np.array([[m[i][j] for j in range(3)] for i in range(3)], dtype=np.float64)


def compute_tracks(
    arm_obj,
    motion,
    mapping,
    *,
    ref_mode="REST",
    align_limbs=True,
    auto_facing=True,
    scale_root=True,
    in_place=False,
    absolute_root=False,
):
    """Compute per-bone keyframe tracks.

    Returns {bone_name: (quats [T,4], locs [T,3] or None)} in pose-bone basis space.
    """
    bones = arm_obj.data.bones
    pbones = arm_obj.pose.bones
    T = motion.num_frames
    mapping = {s: t for s, t in mapping.items() if t and t in bones and s in motion.names}
    if not mapping:
        raise ValueError("No bones are mapped.")
    tgt_to_src = {t: motion.index(s) for s, t in mapping.items()}

    # reference pose (armature space) per bone
    if ref_mode == "CURRENT":
        ref_mat = {b.name: pbones[b.name].matrix.copy() for b in bones}
        ref_basis = {b.name: pbones[b.name].matrix_basis.copy() for b in bones}
    else:
        ref_mat = {b.name: b.matrix_local.copy() for b in bones}
        ref_basis = {b.name: Matrix.Identity(4) for b in bones}

    mw = arm_obj.matrix_world.copy()
    mw_inv = mw.inverted_safe()
    Ow = _np3(mw.to_quaternion().to_matrix())

    def world_head(bname):
        return mw @ ref_mat[bname].translation

    # facing: rotate the motion so the source's left (+X) matches the target's left side
    F = np.eye(3)
    if auto_facing:
        canon = CANON[motion.skeleton_name]
        for part in ("thigh", "upperarm", "shoulder"):
            l_src, r_src = canon.get(f"{part}.L"), canon.get(f"{part}.R")
            if l_src in mapping and r_src in mapping:
                d = world_head(mapping[l_src]) - world_head(mapping[r_src])
                if d.x * d.x + d.y * d.y > 1e-10:
                    yaw = math.atan2(d.y, d.x)
                    c, s = math.cos(yaw), math.sin(yaw)
                    F = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
                break

    # limb alignment (source rest direction vs target reference direction)
    align_src = set()
    if align_limbs:
        canon = CANON[motion.skeleton_name]
        for part in ALIGN_PARTS:
            for side in ("L", "R"):
                src = canon.get(f"{part}.{side}")
                if src:
                    align_src.add(src)

    # constant right factor K_b = A_b @ Ow @ ref_rot_b, then R_arm(t) = Ow^T @ F G(t) F^T @ K_b
    Fd = F
    rot_tracks = {}
    for tname, j in tgt_to_src.items():
        ref_rot = ref_mat[tname].to_3x3().normalized()
        W_ref = Ow @ _np3(ref_rot)
        A = np.eye(3)
        if motion.names[j] in align_src:
            src_dir = motion.rest_direction(j)
            if src_dir is not None:
                src_dir = Vector(Fd @ np.array(src_dir))
                tgt_dir = Vector(W_ref @ np.array([0.0, 1.0, 0.0]))
                A = _np3(tgt_dir.rotation_difference(src_dir).to_matrix())
        K = A @ W_ref
        D = np.einsum("ij,tjk,lk->til", Fd, motion.G[:, j], Fd)  # F G F^T
        rot_tracks[tname] = np.einsum("ji,tjk,kl->til", Ow, D, K)  # Ow^T D K

    # root motion
    root_src = motion.names[motion.root]
    root_bone = mapping.get(root_src)
    root_locs_arm = None
    if root_bone:
        Proot = motion.P[:, motion.root]
        if absolute_root:
            world = Proot
        else:
            heads_z = []
            for b in bones:
                heads_z.append((mw @ ref_mat[b.name].translation).z)
                heads_z.append((mw @ (ref_mat[b.name] @ Vector((0.0, b.length, 0.0)))).z)
            ground = min(heads_z)
            hips_ref = world_head(root_bone)
            s = 1.0
            if scale_root:
                src_h = motion.rest_hip_height()
                tgt_h = hips_ref.z - ground
                if src_h > 1e-4 and tgt_h > 1e-4:
                    s = tgt_h / src_h
            rel = Proot.copy()
            rel[:, 0] -= Proot[0, 0]
            rel[:, 1] -= Proot[0, 1]
            if in_place:
                rel[:, :2] = 0.0
            world = (rel * s) @ F.T
            world[:, 0] += hips_ref.x
            world[:, 1] += hips_ref.y
            world[:, 2] += ground
        root_locs_arm = [mw_inv @ Vector(p) for p in world]

    # hierarchy: only mapped bones and their ancestors are needed
    needed = set()
    for tname in tgt_to_src:
        b = bones[tname]
        while b is not None and b.name not in needed:
            needed.add(b.name)
            b = b.parent
    order = sorted(needed, key=lambda n: _bone_depth(bones[n]))
    local_rest = {}
    for n in order:
        b = bones[n]
        local_rest[n] = (b.parent.matrix_local.inverted_safe() @ b.matrix_local) if b.parent else b.matrix_local.copy()
    ref_basis_t = {n: Matrix.Translation(ref_basis[n].translation) for n in order}

    quats = {n: np.empty((T, 4)) for n in tgt_to_src}
    locs = {root_bone: np.empty((T, 3))} if root_bone else {}

    for t in range(T):
        M = {}
        for n in order:
            b = bones[n]
            pc = (M[b.parent.name] @ local_rest[n]) if b.parent else local_rest[n]
            if n in tgt_to_src:
                R = _m3(rot_tracks[n][t])
                if n == root_bone:
                    trans = root_locs_arm[t]
                else:
                    trans = (pc @ ref_basis_t[n]).translation
                Mb = Matrix.Translation(trans) @ R.to_4x4()
                basis = pc.inverted_safe() @ Mb
                loc, q, _ = basis.decompose()
                if t > 0:
                    prev = quats[n][t - 1]
                    if prev[0] * q.w + prev[1] * q.x + prev[2] * q.y + prev[3] * q.z < 0.0:
                        q.negate()
                quats[n][t] = (q.w, q.x, q.y, q.z)
                if n == root_bone:
                    locs[n][t] = loc
                M[n] = Mb
            else:
                M[n] = pc @ ref_basis[n]

    return {n: (quats[n], locs.get(n)) for n in tgt_to_src}


def _action_fcurves(action, anim_data):
    try:
        from bpy_extras import anim_utils

        slot = getattr(anim_data, "action_slot", None)
        if slot is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
            cb = anim_utils.action_get_channelbag_for_slot(action, slot)
            if cb is not None:
                return cb.fcurves
    except ImportError:
        pass
    return action.fcurves


def write_action(arm_obj, tracks, frame_start, action_name):
    anim = arm_obj.animation_data_create()
    action = bpy.data.actions.new(action_name)
    anim.action = action

    for name, (q, loc) in tracks.items():
        pb = arm_obj.pose.bones[name]
        pb.rotation_mode = "QUATERNION"
        pb.keyframe_insert("rotation_quaternion", frame=frame_start, group=name)
        if loc is not None:
            pb.keyframe_insert("location", frame=frame_start, group=name)

    fcurves = {(fc.data_path, fc.array_index): fc for fc in _action_fcurves(action, anim)}
    T = None
    for name, (q, loc) in tracks.items():
        T = len(q)
        frames = np.arange(T, dtype=np.float64) + frame_start
        channels = [("rotation_quaternion", q)]
        if loc is not None:
            channels.append(("location", loc))
        for prop, values in channels:
            path = f'pose.bones["{bpy.utils.escape_identifier(name)}"].{prop}'
            for i in range(values.shape[1]):
                fc = fcurves.get((path, i))
                if fc is None:
                    continue
                kp = fc.keyframe_points
                if len(kp) < T:
                    kp.add(T - len(kp))
                co = np.empty(2 * T)
                co[0::2] = frames
                co[1::2] = values[:, i]
                kp.foreach_set("co", co)
                kp.foreach_set("handle_left", co)
                kp.foreach_set("handle_right", co)
                fc.update()
    return action, T


def _apply_scene_timing(context, settings, frame_start, num_frames):
    scene = context.scene
    if settings.set_scene_fps:
        scene.render.fps = settings.fps
        scene.render.fps_base = 1.0
    scene.frame_start = frame_start
    scene.frame_end = frame_start + num_frames - 1


# ----------------------------------------------------------------------------------------
# Source armature creation
# ----------------------------------------------------------------------------------------


def create_source_armature(context, motion, name):
    arm_data = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm_data)
    context.collection.objects.link(arm_obj)
    arm_data.display_type = "STICK"

    view_layer = context.view_layer
    for o in context.selected_objects:
        o.select_set(False)
    arm_obj.select_set(True)
    view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = []
    for j, jname in enumerate(motion.names):
        eb = arm_data.edit_bones.new(jname)
        head = Vector(motion.rest[j])
        c = motion.main_child(j)
        tail = None
        if c is not None and j != motion.root:
            d = Vector(motion.rest[c]) - head
            if d.length > 0.005:
                tail = head + d
        if tail is None:
            p = motion.parents[j]
            if j == motion.root or p < 0:
                tail = head + Vector((0.0, 0.0, 0.1))
            else:
                d = head - Vector(motion.rest[p])
                tail = head + (d.normalized() * 0.03 if d.length > 1e-6 else Vector((0.0, 0.0, 0.03)))
        eb.head, eb.tail, eb.roll = head, tail, 0.0
        ebones.append(eb)
    for j, p in enumerate(motion.parents):
        if p >= 0:
            ebones[j].parent = ebones[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


# ----------------------------------------------------------------------------------------
# Properties
# ----------------------------------------------------------------------------------------


def _armature_poll(self, obj):
    return obj.type == "ARMATURE"


class KIMODO_BoneMapItem(PropertyGroup):
    source: StringProperty(name="Kimodo joint")
    target: StringProperty(name="Target bone")


class KIMODO_Settings(PropertyGroup):
    filepath: StringProperty(name="NPZ file", subtype="FILE_PATH", description="Kimodo motion .npz")
    fps: IntProperty(name="FPS", default=30, min=1, max=240, description="Frame rate of the Kimodo motion")
    set_scene_fps: BoolProperty(name="Set scene FPS / range", default=True)
    frame_start: IntProperty(name="Start frame", default=1)
    target: PointerProperty(name="Target rig", type=bpy.types.Object, poll=_armature_poll)
    skeleton: StringProperty(name="Skeleton", default="")
    mapping: CollectionProperty(type=KIMODO_BoneMapItem)
    mapping_index: IntProperty()
    show_unmapped: BoolProperty(name="Show unmapped joints", default=False)
    ref_mode: EnumProperty(
        name="Reference pose",
        items=[
            ("REST", "Rest pose", "Target rest pose is treated as the Kimodo T-pose"),
            ("CURRENT", "Current pose", "Current pose of the target is treated as the Kimodo T-pose"),
        ],
        default="REST",
    )
    align_limbs: BoolProperty(
        name="Auto-align limbs",
        default=True,
        description="Compensate rest-pose differences of arms/legs (e.g. A-pose rigs)",
    )
    auto_facing: BoolProperty(
        name="Auto-detect facing", default=True, description="Detect which way the target character faces"
    )
    scale_root: BoolProperty(
        name="Scale root motion", default=True, description="Scale root translation by hip height ratio"
    )
    in_place: BoolProperty(name="In place", default=False, description="Remove horizontal root translation")


# ----------------------------------------------------------------------------------------
# Operators
# ----------------------------------------------------------------------------------------


def _load_motion(op, path):
    path = bpy.path.abspath(path)
    if not path or not os.path.isfile(path):
        op.report({"ERROR"}, f"NPZ file not found: {path!r}")
        return None
    try:
        return KimodoMotion(path)
    except Exception as e:  # noqa: BLE001
        op.report({"ERROR"}, str(e))
        return None


def _fill_mapping(settings, motion, mapping):
    settings.mapping.clear()
    for n in motion.names:
        item = settings.mapping.add()
        item.source = n
        item.target = mapping.get(n, "")
    settings.skeleton = motion.skeleton_name


class KIMODO_OT_import_npz(Operator, ImportHelper):
    """Import a Kimodo NPZ motion as a new animated armature"""

    bl_idname = "kimodo.import_npz"
    bl_label = "Import Kimodo Motion (.npz)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".npz"
    filter_glob: StringProperty(default="*.npz", options={"HIDDEN"})
    fps: IntProperty(name="FPS", default=30, min=1, max=240)
    set_scene_fps: BoolProperty(name="Set scene FPS / range", default=True)
    frame_start: IntProperty(name="Start frame", default=1)
    use_panel_file: BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        if self.use_panel_file:
            return self.execute(context)
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        settings = context.scene.kimodo
        if self.use_panel_file:
            path = settings.filepath
            fps, set_fps, start = settings.fps, settings.set_scene_fps, settings.frame_start
        else:
            path = self.filepath
            fps, set_fps, start = self.fps, self.set_scene_fps, self.frame_start
            settings.filepath = path
        motion = _load_motion(self, path)
        if motion is None:
            return {"CANCELLED"}
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        base = os.path.splitext(os.path.basename(bpy.path.abspath(path)))[0]
        arm_obj = create_source_armature(context, motion, f"Kimodo_{base}")
        tracks = compute_tracks(
            arm_obj,
            motion,
            {n: n for n in motion.names},
            align_limbs=False,
            auto_facing=False,
            absolute_root=True,
        )
        write_action(arm_obj, tracks, start, f"Kimodo_{base}")
        if set_fps:
            context.scene.render.fps = fps
            context.scene.render.fps_base = 1.0
        context.scene.frame_start = start
        context.scene.frame_end = start + motion.num_frames - 1
        self.report({"INFO"}, f"Imported {motion.num_frames} frames ({motion.skeleton_name})")
        return {"FINISHED"}


class KIMODO_OT_auto_map(Operator):
    """Detect the Kimodo skeleton from the NPZ and guess the bone mapping for the target rig"""

    bl_idname = "kimodo.auto_map"
    bl_label = "Auto-map Bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.kimodo
        if settings.target is None:
            self.report({"ERROR"}, "Pick a target armature first")
            return {"CANCELLED"}
        motion = _load_motion(self, settings.filepath)
        if motion is None:
            return {"CANCELLED"}
        mapping = auto_map(settings.target, motion)
        _fill_mapping(settings, motion, mapping)
        canon = CANON[motion.skeleton_name]
        core = [v for k, v in canon.items() if isinstance(v, str)]
        missing = [n for n in core if n not in mapping]
        msg = f"{motion.skeleton_name}: mapped {len(mapping)} joints"
        if missing:
            msg += f"; unmapped body joints: {', '.join(missing)}"
            self.report({"WARNING"}, msg)
        else:
            self.report({"INFO"}, msg)
        return {"FINISHED"}


class KIMODO_OT_clear_map(Operator):
    """Clear all target bones from the mapping"""

    bl_idname = "kimodo.clear_map"
    bl_label = "Clear Mapping"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for item in context.scene.kimodo.mapping:
            item.target = ""
        return {"FINISHED"}


class KIMODO_OT_apply(Operator):
    """Retarget the Kimodo motion onto the target rig and bake it into a new action"""

    bl_idname = "kimodo.apply"
    bl_label = "Apply Motion to Rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.kimodo
        arm = settings.target
        if arm is None:
            self.report({"ERROR"}, "Pick a target armature first")
            return {"CANCELLED"}
        motion = _load_motion(self, settings.filepath)
        if motion is None:
            return {"CANCELLED"}
        if settings.skeleton != motion.skeleton_name or not len(settings.mapping):
            _fill_mapping(settings, motion, auto_map(arm, motion))
        mapping = {it.source: it.target for it in settings.mapping if it.target}
        if not mapping:
            self.report({"ERROR"}, "Bone mapping is empty; map at least the hips")
            return {"CANCELLED"}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if settings.ref_mode == "REST":
            for pb in arm.pose.bones:
                pb.matrix_basis = Matrix.Identity(4)
        context.view_layer.update()

        try:
            tracks = compute_tracks(
                arm,
                motion,
                mapping,
                ref_mode=settings.ref_mode,
                align_limbs=settings.align_limbs,
                auto_facing=settings.auto_facing,
                scale_root=settings.scale_root,
                in_place=settings.in_place,
            )
        except Exception as e:  # noqa: BLE001
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        base = os.path.splitext(os.path.basename(bpy.path.abspath(settings.filepath)))[0]
        write_action(arm, tracks, settings.frame_start, f"Kimodo_{base}_{arm.name}")
        _apply_scene_timing(context, settings, settings.frame_start, motion.num_frames)
        self.report({"INFO"}, f"Applied {motion.num_frames} frames to {arm.name} ({len(tracks)} bones)")
        return {"FINISHED"}


# ----------------------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------------------


class KIMODO_UL_bone_map(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        arm = context.scene.kimodo.target
        row = layout.row(align=True)
        split = row.split(factor=0.4)
        split.label(text=item.source)
        if arm is not None and arm.type == "ARMATURE":
            split.prop_search(item, "target", arm.data, "bones", text="")
        else:
            split.prop(item, "target", text="")

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        show_all = context.scene.kimodo.show_unmapped
        flags = [self.bitflag_filter_item if (show_all or it.target) else 0 for it in items]
        return flags, []


class KIMODO_PT_panel(Panel):
    bl_label = "Kimodo Motion"
    bl_idname = "KIMODO_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Kimodo"

    def draw(self, context):
        s = context.scene.kimodo
        layout = self.layout

        col = layout.column(align=True)
        col.prop(s, "filepath", text="")
        row = col.row(align=True)
        row.prop(s, "fps")
        row.prop(s, "frame_start", text="Start")
        col.prop(s, "set_scene_fps")
        op = layout.operator(KIMODO_OT_import_npz.bl_idname, text="Import as Kimodo Skeleton", icon="ARMATURE_DATA")
        op.use_panel_file = True

        box = layout.box()
        box.label(text="Retarget to rig", icon="MOD_ARMATURE")
        box.prop(s, "target")
        row = box.row(align=True)
        row.operator(KIMODO_OT_auto_map.bl_idname, icon="AUTO")
        row.operator(KIMODO_OT_clear_map.bl_idname, text="", icon="X")
        if len(s.mapping):
            box.label(text=f"Bone map ({s.skeleton})")
            box.template_list("KIMODO_UL_bone_map", "", s, "mapping", s, "mapping_index", rows=8)
            box.prop(s, "show_unmapped")

        sub = box.column(align=True)
        sub.prop(s, "ref_mode", text="")
        sub.prop(s, "align_limbs")
        sub.prop(s, "auto_facing")
        sub.prop(s, "scale_root")
        sub.prop(s, "in_place")
        box.operator(KIMODO_OT_apply.bl_idname, icon="PLAY")


def _menu_import(self, context):
    self.layout.operator(KIMODO_OT_import_npz.bl_idname, text="Kimodo Motion (.npz)")


_classes = (
    KIMODO_BoneMapItem,
    KIMODO_Settings,
    KIMODO_OT_import_npz,
    KIMODO_OT_auto_map,
    KIMODO_OT_clear_map,
    KIMODO_OT_apply,
    KIMODO_UL_bone_map,
    KIMODO_PT_panel,
)


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.kimodo = PointerProperty(type=KIMODO_Settings)
    bpy.types.TOPBAR_MT_file_import.append(_menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(_menu_import)
    del bpy.types.Scene.kimodo
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
