"""
╔══════════════════════════════════════════════════════════════╗
║           STARK LAB v5  —  Real-Time Gesture Edition         ║
║     Webcam · MediaPipe · PyOpenGL · Smooth Gestures          ║
╚══════════════════════════════════════════════════════════════╝

RUN:
  python3 starklab.py /home/knight/MK1.STL
  python3 starklab.py                        ← drag & drop

GESTURES:
  ✋  Open Hand  + wave RIGHT  → Rotate clockwise   (smooth)
  ✋  Open Hand  + wave LEFT   → Rotate anti-clock  (smooth)
  🤏  Pinch      + move UP     → Zoom in            (smooth)
  🤏  Pinch      + move DOWN   → Zoom out           (smooth)
  ☝   Point      + move UP/DN  → Tilt X-axis
  ✊  Fist                     → Lock / freeze
  👌  OK                       → Reset all

  2.5 s hold before switching gesture — prevents accidents.
  Fist & OK switch instantly.

KEYBOARD:
  S → auto-spin    R → reset    ESC → quit
"""

import sys, os, math, time, struct, threading
import numpy as np
import cv2
import glfw
from OpenGL.GL  import *
from OpenGL.GLU import *

# ── MediaPipe ────────────────────────────────────────────────
try:
    import mediapipe as mp
    _mp_hands   = mp.solutions.hands
    _mp_drawing = mp.solutions.drawing_utils
    _mp_styles  = mp.solutions.drawing_styles
    Hands        = _mp_hands.Hands
    MEDIAPIPE_OK = True
    print("[MP] MediaPipe OK")
except Exception as e:
    MEDIAPIPE_OK = False
    print(f"[MP] MediaPipe unavailable ({e})  →  mouse-rotate only")


# ══════════════════════════════════════════════════════════════
#  STL LOADER
# ══════════════════════════════════════════════════════════════

class STLMesh:
    def __init__(self):
        self.vertices = np.zeros(0, dtype=np.float32)
        self.normals  = np.zeros(0, dtype=np.float32)
        self.loaded   = False
        self.filename = ""

    def load(self, filepath):
        filepath = filepath.strip()
        if not os.path.isfile(filepath):
            print(f"[STL] Not found: '{filepath}'"); return
        print(f"[STL] Loading: {filepath}")
        try:
            verts, norms = (self._load_binary(filepath)
                            if self._is_binary(filepath)
                            else self._load_ascii(filepath))
            if not verts:
                print("[STL] No vertices!"); return
            self.vertices = np.array(verts, dtype=np.float32)
            self.normals  = np.array(norms, dtype=np.float32)
            self._normalize()
            self.loaded   = True
            self.filename = os.path.basename(filepath)
            print(f"[STL] {len(self.vertices)//9} triangles  ✓")
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"[STL] ERROR: {e}")

    def _is_binary(self, path):
        with open(path,'rb') as f: raw = f.read(256)
        t = raw[:5].decode('ascii','ignore').strip().lower()
        return t != 'solid' or 'facet' not in raw.decode('ascii','ignore')

    def _load_binary(self, path):
        v, n = [], []
        with open(path,'rb') as f:
            f.read(80)
            count = struct.unpack('<I', f.read(4))[0]
            for _ in range(count):
                d = f.read(50)
                if len(d) < 50: break
                nx,ny,nz = struct.unpack_from('<fff',d,0)
                for off in (12,24,36):
                    x,y,z = struct.unpack_from('<fff',d,off)
                    v+=[x,y,z]; n+=[nx,ny,nz]
        return v, n

    def _load_ascii(self, path):
        v, n, cur = [], [], [0.,0.,1.]
        with open(path,'r',errors='ignore') as f:
            for line in f:
                l = line.strip()
                if l.startswith('facet normal'):
                    p=l.split(); cur=[float(p[2]),float(p[3]),float(p[4])]
                elif l.startswith('vertex'):
                    p=l.split(); v+=[float(p[1]),float(p[2]),float(p[3])]; n+=cur
        return v, n

    def _normalize(self):
        v  = self.vertices.reshape(-1,3)
        mn,mx = v.min(0), v.max(0)
        c  = (mn+mx)/2.; span = float((mx-mn).max())
        sc = 2./span if span>1e-9 else 1.
        v  = (v-c)*sc
        self.vertices = v.flatten().astype(np.float32)
        # fix zero normals
        nr = self.normals.reshape(-1,3)
        bad = np.linalg.norm(nr,axis=1)<1e-6
        if bad.any():
            vt = v.reshape(-1,3,3)
            fn = np.cross(vt[:,1]-vt[:,0], vt[:,2]-vt[:,0])
            fl = np.linalg.norm(fn,axis=1,keepdims=True)
            fn /= np.where(fl<1e-9,1.,fl)
            fn3 = np.repeat(fn,3,axis=0)
            bad3 = np.repeat(bad.reshape(-1,3)[:,0:1],3,axis=1).flatten()
            nr[bad3] = fn3[bad3]
            self.normals = nr.flatten().astype(np.float32)


# ══════════════════════════════════════════════════════════════
#  HAND TRACKER  — background thread
# ══════════════════════════════════════════════════════════════

class HandTracker:
    NONE  = "none"
    OPEN  = "open"
    FIST  = "fist"
    PINCH = "pinch"
    POINT = "point"
    OK    = "ok"

    # landmark indices
    _TIPS = [8,12,16,20]
    _PIPS = [6,10,14,18]

    def __init__(self, cam=0):
        self.cap = cv2.VideoCapture(cam)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam {cam}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self._hands = Hands(
            static_image_mode=False, max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6)

        self._lock      = threading.Lock()
        self._gesture   = self.NONE
        self._hx = .5;  self._hy = .5
        self._dx = .0;  self._dy = .0
        self._wave      = 0
        self._xhist     = []

        # smoothed velocity accumulators (exposed for smooth movement)
        self._vx = 0.; self._vy = 0.

        # camera frame with landmarks drawn (for preview)
        self._preview   = None   # BGR numpy array 320×240

        self._running   = True
        threading.Thread(target=self._loop, daemon=True).start()
        print(f"[CAM] Webcam {cam} started")

    # ── background loop ───────────────────────────────────────

    def _loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if not ok: time.sleep(0.01); continue

            frame = cv2.flip(frame, 1)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res   = self._hands.process(rgb)

            # draw landmarks on frame copy
            vis = frame.copy()
            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0]
                if MEDIAPIPE_OK:
                    _mp_drawing.draw_landmarks(
                        vis, lm,
                        _mp_hands.HAND_CONNECTIONS,
                        _mp_styles.get_default_hand_landmarks_style(),
                        _mp_styles.get_default_hand_connections_style())
                self._update(lm.landmark)
            else:
                with self._lock:
                    self._gesture = self.NONE
                    self._wave    = 0
                    self._vx      = 0.
                    self._vy      = 0.

            # store preview
            with self._lock:
                self._preview = vis

    def _update(self, lm):
        wx, wy = lm[0].x, lm[0].y
        self._xhist.append(wx)
        if len(self._xhist) > 15: self._xhist.pop(0)
        with self._lock:
            raw_dx = wx - self._hx
            raw_dy = wy - self._hy
            # exponential smoothing on velocity
            alpha  = 0.35
            self._vx = alpha*raw_dx + (1-alpha)*self._vx
            self._vy = alpha*raw_dy + (1-alpha)*self._vy
            self._dx = self._vx
            self._dy = self._vy
            self._hx = wx;  self._hy = wy
            self._gesture = self._classify(lm)
            self._wave    = self._wave_dir()

    def _classify(self, lm):
        up = [lm[self._TIPS[i]].y < lm[self._PIPS[i]].y for i in range(4)]
        pinch = math.hypot(lm[4].x-lm[8].x, lm[4].y-lm[8].y)
        if all(up):                                       return self.OPEN
        if not any(up):
            return self.PINCH if pinch < 0.07 else self.FIST
        if up[0] and not up[1] and not up[2] and not up[3]: return self.POINT
        if pinch < 0.07 and up[1] and up[2] and up[3]:   return self.OK
        return self.NONE

    def _wave_dir(self):
        if len(self._xhist) < 8: return 0
        d   = [self._xhist[i+1]-self._xhist[i] for i in range(len(self._xhist)-1)]
        avg = sum(d)/len(d)
        return 1 if avg>0.006 else (-1 if avg<-0.006 else 0)

    def get(self):
        with self._lock:
            return dict(gesture=self._gesture,
                        dx=self._dx, dy=self._dy,
                        wave=self._wave,
                        preview=self._preview)

    def stop(self):
        self._running = False
        self.cap.release()


# ══════════════════════════════════════════════════════════════
#  STARK LAB  —  main app
# ══════════════════════════════════════════════════════════════

# Gesture meta info (icon, label, colour RGB 0-1)
GESTURE_INFO = {
    HandTracker.OPEN  if MEDIAPIPE_OK else "open":
        ("✋", "ROTATE",  (0.0, 0.85, 1.0)),
    HandTracker.PINCH if MEDIAPIPE_OK else "pinch":
        ("🤏", "SCALE",   (1.0, 0.75, 0.0)),
    HandTracker.POINT if MEDIAPIPE_OK else "point":
        ("☝",  "TILT",    (0.4, 1.0,  0.4)),
    HandTracker.FIST  if MEDIAPIPE_OK else "fist":
        ("✊", "LOCKED",  (1.0, 0.3,  0.3)),
    HandTracker.OK    if MEDIAPIPE_OK else "ok":
        ("👌", "RESET",   (1.0, 1.0,  1.0)),
    "none":             ("·",  "STANDBY", (0.4, 0.4,  0.5)),
}

GESTURE_DELAY = 2.5   # seconds before switching active gesture

class StarkLab:
    W, H = 1280, 720

    # camera preview box (bottom-right corner)
    CAM_W, CAM_H   = 280, 210
    CAM_PAD        = 14

    def __init__(self, stl_path=None, cam=0):
        self.stl_path = stl_path
        self.cam      = cam
        self.mesh     = STLMesh()
        self.tracker  = None

        # transform  (smooth targets + current)
        self.rot_x    = 20.0;   self._tgt_rx = 20.0
        self.rot_y    = 0.0;    self._tgt_ry = 0.0
        self.scale    = 1.0;    self._tgt_sc = 1.0

        # VBO
        self.vbo_v = None;  self.vbo_n = None;  self.n_vtx = 0

        # gesture state machine
        self._active_g  = HandTracker.NONE
        self._pending_g = HandTracker.NONE
        self._pend_t    = 0.0
        self._countdown = 0.0

        # indicator animation
        self._ind_alpha = 0.0      # 0..1 fade in/out
        self._ind_scale = 1.0      # pulse scale

        # misc
        self.spin        = False
        self.label       = "STARK LAB"
        self.fps         = 0
        self._ft         = []
        self._drop_p     = None
        self._drop_flash = 0.0
        self._mouse_dn   = False
        self._mx0 = 0.;  self._my0 = 0.

        # camera texture
        self._cam_tex    = None
        self._cam_frame  = None   # latest BGR frame

    # ── window / GL ───────────────────────────────────────────

    def _init_window(self):
        if not glfw.init(): raise RuntimeError("glfw.init() failed")
        glfw.window_hint(glfw.SAMPLES, 4)
        self.win = glfw.create_window(self.W, self.H, "STARK LAB", None, None)
        if not self.win: glfw.terminate(); raise RuntimeError("window failed")
        glfw.make_context_current(self.win)
        glfw.set_key_callback(self.win,          self._on_key)
        glfw.set_drop_callback(self.win,         self._on_drop)
        glfw.set_mouse_button_callback(self.win, self._on_mbtn)
        glfw.set_cursor_pos_callback(self.win,   self._on_cur)
        glfw.swap_interval(1)
        self._setup_gl()
        self._build_grid()
        self._cam_tex = glGenTextures(1)

    def _setup_gl(self):
        glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0);     glEnable(GL_LIGHT1)
        glEnable(GL_COLOR_MATERIAL); glEnable(GL_NORMALIZE)
        glEnable(GL_MULTISAMPLE);    glShadeModel(GL_SMOOTH)
        glLightfv(GL_LIGHT0, GL_POSITION, [ 5., 8., 6., 1.])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [ 1., .98,.95, 1.])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [ 1., 1., 1., 1.])
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [.15,.15,.2,  1.])
        glLightfv(GL_LIGHT1, GL_POSITION, [-4.,-3.,-3., 1.])
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [.3, .5, .8,  1.])
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [.9,.95,1.,1.])
        glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 96.)
        glClearColor(.02,.04,.10,1.)

    def _build_grid(self):
        self.grid_dl = glGenLists(1)
        glNewList(self.grid_dl, GL_COMPILE)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(1.)
        size, step = 5., .3
        glBegin(GL_LINES)
        x = -size
        while x <= size+.001:
            t = 1.-abs(x)/size
            glColor4f(.0,.5,1.,.18*t)
            glVertex3f(x,-1.6,-size); glVertex3f(x,-1.6, size)
            x += step
        z = -size
        while z <= size+.001:
            t = 1.-abs(z)/size
            glColor4f(.0,.5,1.,.18*t)
            glVertex3f(-size,-1.6,z); glVertex3f( size,-1.6,z)
            z += step
        glEnd()
        glDisable(GL_BLEND); glEnable(GL_LIGHTING)
        glEndList()

    # ── VBO ───────────────────────────────────────────────────

    def _upload(self):
        if not self.mesh.loaded: return
        if self.vbo_v:
            glDeleteBuffers(1,[self.vbo_v]); glDeleteBuffers(1,[self.vbo_n])
        self.vbo_v = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_v)
        glBufferData(GL_ARRAY_BUFFER, self.mesh.vertices.nbytes,
                     self.mesh.vertices, GL_STATIC_DRAW)
        self.vbo_n = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_n)
        glBufferData(GL_ARRAY_BUFFER, self.mesh.normals.nbytes,
                     self.mesh.normals, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.n_vtx = len(self.mesh.vertices)//3
        print(f"[GL] VBO ready  {self.n_vtx} vertices")

    # ── drag-drop ─────────────────────────────────────────────

    def _on_drop(self, win, paths):
        for p in paths:
            if p.lower().endswith('.stl'):
                self._drop_p = p; self._drop_flash = 1.; return
        print("[DROP] Not an STL")

    def _handle_drop(self):
        if self._drop_p:
            p = self._drop_p; self._drop_p = None
            self.mesh.load(p); self._upload(); self._reset_transform()

    # ── mouse fallback ────────────────────────────────────────

    def _on_mbtn(self, win, btn, act, mods):
        if btn == glfw.MOUSE_BUTTON_LEFT:
            self._mouse_dn = (act == glfw.PRESS)
            self._mx0, self._my0 = glfw.get_cursor_pos(win)

    def _on_cur(self, win, mx, my):
        if self._mouse_dn:
            dx = mx - self._mx0;  dy = my - self._my0
            self._tgt_ry += dx * 0.4
            self._tgt_rx += dy * 0.4
            self._mx0, self._my0 = mx, my

    # ── gesture state machine ─────────────────────────────────

    def _process_gestures(self, dt):
        if not self.tracker: return
        s    = self.tracker.get()
        g    = s["gesture"]
        wave = s["wave"]
        dy   = s["dy"]
        now  = time.time()

        # store latest camera frame
        if s["preview"] is not None:
            self._cam_frame = s["preview"]

        # instant gestures bypass the delay
        instant = g in (HandTracker.OK, HandTracker.FIST, HandTracker.NONE)

        # ── transition gate ────────────────────────────────────
        if g != self._active_g:
            if instant:
                self._active_g  = g
                self._pending_g = g
                self._countdown = 0.
            elif g != self._pending_g:
                self._pending_g = g
                self._pend_t    = now
                self._countdown = GESTURE_DELAY
                print(f"[GESTURE] pending '{g}'  ({GESTURE_DELAY:.0f}s)")
            else:
                elapsed = now - self._pend_t
                self._countdown = max(0., GESTURE_DELAY - elapsed)
                if self._countdown == 0.:
                    self._active_g = g
                    print(f"[GESTURE] ACTIVE  '{g}'")
        else:
            self._pending_g = g
            self._countdown = 0.

        # ── indicator fade ─────────────────────────────────────
        target_alpha = 0. if self._active_g == HandTracker.NONE else 1.
        self._ind_alpha += (target_alpha - self._ind_alpha) * min(1., dt*6)
        self._ind_scale  = 1. + .06*abs(math.sin(time.time()*3))

        # ── apply active gesture to smooth targets ─────────────
        ag = self._active_g

        ROT_SPD   = 120.   # deg/s for wave rotation
        ZOOM_SPD  = 2.5    # scale units/s for pinch
        TILT_SPD  = 80.

        if ag == HandTracker.OPEN:
            if   wave ==  1: self._tgt_ry += ROT_SPD  * dt
            elif wave == -1: self._tgt_ry -= ROT_SPD  * dt

        elif ag == HandTracker.PINCH:
            # natural: move hand UP = zoom in, DOWN = zoom out
            # dy is negative when hand moves up (screen coords)
            zoom_delta   = -dy * ZOOM_SPD * 60. * dt
            self._tgt_sc = max(.05, min(15., self._tgt_sc + zoom_delta))

        elif ag == HandTracker.POINT:
            self._tgt_rx += dy * TILT_SPD * 60. * dt

        elif ag == HandTracker.OK:
            self._reset_transform()
            self._active_g  = HandTracker.NONE
            self._pending_g = HandTracker.NONE

        # ── smooth interpolation (lerp) toward targets ─────────
        LERP = min(1., dt * 10.)    # 10 = snappy but smooth
        self.rot_x += (self._tgt_rx - self.rot_x) * LERP
        self.rot_y += (self._tgt_ry - self.rot_y) * LERP
        self.scale += (self._tgt_sc - self.scale) * LERP

        # ── label ──────────────────────────────────────────────
        if self._countdown > 0.:
            icon, name, _ = GESTURE_INFO.get(self._pending_g,
                                             ("·","...", (1,1,1)))
            self.label = f"⏳ {icon} {name} in {self._countdown:.1f}s"
        else:
            icon, name, _ = GESTURE_INFO.get(ag, ("·","STANDBY",(1,1,1)))
            if ag == HandTracker.OPEN:
                arrow = " ▶" if wave==1 else (" ◀" if wave==-1 else "")
                self.label = f"{icon} ROTATE{arrow}"
            elif ag == HandTracker.PINCH:
                self.label = f"{icon} SCALE  {self.scale:.2f}×"
            else:
                self.label = f"{icon} {name}"

    def _reset_transform(self):
        self.rot_x = 20.; self._tgt_rx = 20.
        self.rot_y = 0.;  self._tgt_ry = 0.
        self.scale = 1.;  self._tgt_sc = 1.

    # ── upload camera frame to GL texture ─────────────────────

    def _update_cam_texture(self):
        if self._cam_frame is None: return
        frame = self._cam_frame
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb   = np.flipud(rgb).astype(np.uint8)
        glBindTexture(GL_TEXTURE_2D, self._cam_tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, rgb)
        glBindTexture(GL_TEXTURE_2D, 0)

    # ── render ────────────────────────────────────────────────

    def _render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        fw, fh = glfw.get_framebuffer_size(self.win)
        glViewport(0, 0, fw, fh)

        # ── 3D projection ──────────────────────────────────────
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45., fw/max(fh,1), .01, 200.)
        glMatrixMode(GL_MODELVIEW);  glLoadIdentity()
        gluLookAt(0,.5,5,  0,0,0,  0,1,0)

        glCallList(self.grid_dl)

        if self.mesh.loaded and self.n_vtx > 0:
            glPushMatrix()
            glScalef(self.scale, self.scale, self.scale)
            glRotatef(self.rot_x, 1,0,0)
            glRotatef(self.rot_y, 0,1,0)

            glColor3f(.05,.88,1.)
            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_n)
            glNormalPointer(GL_FLOAT, 0, None)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_v)
            glVertexPointer(3, GL_FLOAT, 0, None)
            glDrawArrays(GL_TRIANGLES, 0, self.n_vtx)
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, 0)

            # wireframe overlay
            glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(.4); glColor4f(0.,1.,1.,.06)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_v)
            glEnableClientState(GL_VERTEX_ARRAY)
            glVertexPointer(3,GL_FLOAT,0,None)
            glDrawArrays(GL_TRIANGLES,0,self.n_vtx)
            glDisableClientState(GL_VERTEX_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER,0)
            glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
            glDisable(GL_BLEND)
            glPopMatrix()
        else:
            glDisable(GL_LIGHTING); glLineWidth(2.5)
            glBegin(GL_LINES)
            glColor3f(1.,.2,.2); glVertex3f(0,0,0); glVertex3f(1.5,0,0)
            glColor3f(.2,1.,.2); glVertex3f(0,0,0); glVertex3f(0,1.5,0)
            glColor3f(.2,.5,1.); glVertex3f(0,0,0); glVertex3f(0,0,1.5)
            glEnd(); glEnable(GL_LIGHTING)

        # ── 2D HUD ─────────────────────────────────────────────
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        glOrtho(0,fw,0,fh,-1,1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

        self._draw_footer(fw, fh)
        self._draw_gesture_indicator(fw, fh)
        self._draw_cam_preview(fw, fh)
        self._draw_dropzone(fw, fh)

        glDisable(GL_BLEND); glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)

    # ── footer bar ────────────────────────────────────────────

    def _draw_footer(self, w, h):
        glColor4f(.0,.08,.22,.85)
        glBegin(GL_QUADS)
        glVertex2f(0,0); glVertex2f(w,0)
        glVertex2f(w,48); glVertex2f(0,48)
        glEnd()
        p = .4+.6*abs(math.sin(time.time()*3))
        glColor4f(.0,p,1.,1.); glLineWidth(2.)
        glBegin(GL_LINES)
        glVertex2f(0,48); glVertex2f(w,48)
        glEnd()

    # ── gesture indicator panel (top-left) ────────────────────

    def _draw_gesture_indicator(self, w, h):
        if self._ind_alpha < .01: return
        a   = self._ind_alpha
        ag  = self._active_g
        pg  = self._pending_g
        g   = ag if self._countdown == 0. else pg
        _, name, col = GESTURE_INFO.get(g, ("·","STANDBY",(0.4,0.4,0.5)))
        r,gr,b = col

        # panel background
        px, py, pw, ph = 16, h-16-90, 220, 90
        glColor4f(.0,.08,.22, .80*a)
        glBegin(GL_QUADS)
        glVertex2f(px,py); glVertex2f(px+pw,py)
        glVertex2f(px+pw,py+ph); glVertex2f(px,py+ph)
        glEnd()

        # coloured left bar
        glColor4f(r,gr,b,a)
        glBegin(GL_QUADS)
        glVertex2f(px,py); glVertex2f(px+4,py)
        glVertex2f(px+4,py+ph); glVertex2f(px,py+ph)
        glEnd()

        # top border line
        glLineWidth(1.5); glColor4f(r,gr,b,.6*a)
        glBegin(GL_LINES)
        glVertex2f(px,py+ph); glVertex2f(px+pw,py+ph)
        glEnd()

        # countdown progress bar
        if self._countdown > 0.:
            prog = 1. - (self._countdown / GESTURE_DELAY)
            glColor4f(r,gr,b,.5*a)
            glBegin(GL_QUADS)
            glVertex2f(px,py); glVertex2f(px+pw*prog,py)
            glVertex2f(px+pw*prog,py+3); glVertex2f(px,py+3)
            glEnd()

    # ── camera preview box (bottom-right) ─────────────────────

    def _draw_cam_preview(self, w, h):
        if self._cam_frame is None: return

        self._update_cam_texture()

        cw, ch = self.CAM_W, self.CAM_H
        pad    = self.CAM_PAD
        x0     = w - cw - pad
        y0     = pad   # bottom of screen (OpenGL y=0 is bottom)

        # border glow
        glColor4f(.0,.7,1.,.5); glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x0-2,y0-2); glVertex2f(x0+cw+2,y0-2)
        glVertex2f(x0+cw+2,y0+ch+2); glVertex2f(x0-2,y0+ch+2)
        glEnd()

        # corner brackets
        s = 12; glLineWidth(2.5)
        p2 = .9+.1*abs(math.sin(time.time()*2))
        glColor4f(.0,p2,1.,1.)
        corners = [(x0,y0,1,1),(x0+cw,y0,-1,1),
                   (x0+cw,y0+ch,-1,-1),(x0,y0+ch,1,-1)]
        glBegin(GL_LINES)
        for cx,cy,sx,sy in corners:
            glVertex2f(cx,cy+sy*s); glVertex2f(cx,cy)
            glVertex2f(cx,cy); glVertex2f(cx+sx*s,cy)
        glEnd()

        # draw camera texture
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self._cam_tex)
        glColor4f(1.,1.,1.,1.)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex2f(x0,   y0)
        glTexCoord2f(1,0); glVertex2f(x0+cw,y0)
        glTexCoord2f(1,1); glVertex2f(x0+cw,y0+ch)
        glTexCoord2f(0,1); glVertex2f(x0,   y0+ch)
        glEnd()
        glDisable(GL_TEXTURE_2D)

        # "CAM" label tag
        glColor4f(.0,.08,.22,.85)
        glBegin(GL_QUADS)
        glVertex2f(x0,y0+ch); glVertex2f(x0+44,y0+ch)
        glVertex2f(x0+44,y0+ch+16); glVertex2f(x0,y0+ch+16)
        glEnd()
        glColor4f(.0,.8,1.,.9); glLineWidth(1.)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x0,y0+ch); glVertex2f(x0+44,y0+ch)
        glVertex2f(x0+44,y0+ch+16); glVertex2f(x0,y0+ch+16)
        glEnd()

    # ── drop zone ─────────────────────────────────────────────

    def _draw_dropzone(self, w, h):
        if not self.mesh.loaded:
            pulse = .3+.3*abs(math.sin(time.time()*1.8))
            pad = 50
            glColor4f(.0,.75,1.,pulse); glLineWidth(1.5)
            glBegin(GL_LINE_LOOP)
            glVertex2f(pad,pad); glVertex2f(w-pad,pad)
            glVertex2f(w-pad,h-pad); glVertex2f(pad,h-pad)
            glEnd()
            s = 30; glLineWidth(3.); glColor4f(.0,.95,1.,.9)
            corners=[(pad,pad,1,1),(w-pad,pad,-1,1),
                     (w-pad,h-pad,-1,-1),(pad,h-pad,1,-1)]
            glBegin(GL_LINES)
            for cx,cy,sx,sy in corners:
                glVertex2f(cx,cy+sy*s); glVertex2f(cx,cy)
                glVertex2f(cx,cy); glVertex2f(cx+sx*s,cy)
            glEnd()
        if self._drop_flash > 0:
            glColor4f(.0,1.,.3,self._drop_flash*.28)
            glBegin(GL_QUADS)
            glVertex2f(0,0); glVertex2f(w,0)
            glVertex2f(w,h); glVertex2f(0,h)
            glEnd()

    # ── keyboard ──────────────────────────────────────────────

    def _on_key(self, win, key, sc, act, mods):
        if act != glfw.PRESS: return
        if   key == glfw.KEY_ESCAPE: glfw.set_window_should_close(win,True)
        elif key == glfw.KEY_R:      self._reset_transform()
        elif key == glfw.KEY_S:      self.spin = not self.spin

    # ── main loop ─────────────────────────────────────────────

    def run(self):
        self._init_window()

        if MEDIAPIPE_OK:
            try:
                self.tracker = HandTracker(self.cam)
            except Exception as e:
                print(f"[CAM] {e}  →  mouse only"); self.tracker = None
        else:
            print("[INFO] Mouse left-drag = rotate")

        if self.stl_path:
            self.mesh.load(self.stl_path); self._upload()
        else:
            print("\n  Drag & drop an STL onto the window")
            print("  OR:  python3 starklab.py /path/to/model.stl\n")

        t0 = time.time()
        while not glfw.window_should_close(self.win):
            now = time.time(); dt = now-t0; t0 = now
            self._ft.append(dt)
            if len(self._ft)>60: self._ft.pop(0)
            avg = sum(self._ft)/len(self._ft)
            self.fps = int(1./avg) if avg>0 else 0

            if self.spin: self._tgt_ry += 35.*dt

            if self._drop_flash>0:
                self._drop_flash = max(0., self._drop_flash - dt/.5)

            self._handle_drop()
            self._process_gestures(dt)
            self._render()

            name = self.mesh.filename if self.mesh.loaded else "no model"
            glfw.set_window_title(
                self.win,
                f"STARK LAB  //  {self.label}  //  {name}  //  "
                f"rot {self.rot_y%360:.0f}°  "
                f"scale {self.scale:.2f}×  {self.fps}fps")

            glfw.swap_buffers(self.win)
            glfw.poll_events()

        if self.tracker: self.tracker.stop()
        glfw.terminate()
        print("[STARK LAB] Shutdown.")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    stl = sys.argv[1] if len(sys.argv)>1 else None
    cam = int(sys.argv[2]) if len(sys.argv)>2 else 0
    StarkLab(stl_path=stl, cam=cam).run()