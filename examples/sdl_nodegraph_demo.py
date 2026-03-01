"""termin-nodegraph interactive demo."""

from __future__ import annotations

import ctypes

import sdl2
from sdl2 import video
from OpenGL.GL import glEnable, GL_MULTISAMPLE

from tcbase import Key, Mods, MouseButton
from tcgui.widgets.ui import UI
from tcgui.widgets.units import pct
from tcgui.widgets.vstack import VStack
from tgfx import OpenGLGraphicsBackend

from tcnodegraph import Graph, GraphController, NodeGraphView


def create_window(title: str, width: int, height: int):
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
        raise RuntimeError(f"SDL_Init failed: {sdl2.SDL_GetError()}")

    video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
    video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, 3)
    video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_PROFILE_MASK, video.SDL_GL_CONTEXT_PROFILE_CORE)
    video.SDL_GL_SetAttribute(video.SDL_GL_DOUBLEBUFFER, 1)
    video.SDL_GL_SetAttribute(video.SDL_GL_DEPTH_SIZE, 24)
    # Request MSAA framebuffer (4x) for smoother UI edges.
    video.SDL_GL_SetAttribute(video.SDL_GL_MULTISAMPLEBUFFERS, 1)
    video.SDL_GL_SetAttribute(video.SDL_GL_MULTISAMPLESAMPLES, 4)

    flags = video.SDL_WINDOW_OPENGL | video.SDL_WINDOW_RESIZABLE | video.SDL_WINDOW_SHOWN
    window = video.SDL_CreateWindow(
        title.encode("utf-8"),
        video.SDL_WINDOWPOS_CENTERED,
        video.SDL_WINDOWPOS_CENTERED,
        width,
        height,
        flags,
    )
    if not window:
        raise RuntimeError(f"SDL_CreateWindow failed: {sdl2.SDL_GetError()}")

    gl_ctx = video.SDL_GL_CreateContext(window)
    if not gl_ctx:
        video.SDL_DestroyWindow(window)
        raise RuntimeError(f"SDL_GL_CreateContext failed: {sdl2.SDL_GetError()}")

    video.SDL_GL_MakeCurrent(window, gl_ctx)
    video.SDL_GL_SetSwapInterval(1)
    return window, gl_ctx


def get_drawable_size(window) -> tuple[int, int]:
    w, h = ctypes.c_int(), ctypes.c_int()
    video.SDL_GL_GetDrawableSize(window, ctypes.byref(w), ctypes.byref(h))
    return w.value, h.value


_KEY_MAP = {
    sdl2.SDL_SCANCODE_DELETE: Key.DELETE,
    sdl2.SDL_SCANCODE_ESCAPE: Key.ESCAPE,
}


def translate_key(scancode: int):
    return _KEY_MAP.get(scancode, Key.UNKNOWN)


def translate_mods(sdl_mods: int) -> int:
    result = 0
    if sdl_mods & (sdl2.KMOD_LSHIFT | sdl2.KMOD_RSHIFT):
        result |= Mods.SHIFT.value
    if sdl_mods & (sdl2.KMOD_LCTRL | sdl2.KMOD_RCTRL):
        result |= Mods.CTRL.value
    if sdl_mods & (sdl2.KMOD_LALT | sdl2.KMOD_RALT):
        result |= Mods.ALT.value
    return result


_SDL_BUTTON_MAP = {1: MouseButton.LEFT, 2: MouseButton.MIDDLE, 3: MouseButton.RIGHT}


def translate_button(sdl_button: int) -> MouseButton:
    return _SDL_BUTTON_MAP.get(sdl_button, MouseButton.LEFT)


def make_demo_graph() -> Graph:
    g = Graph()
    c = GraphController(g)

    a = c.create_node("pass", title="ColorPass", x=-260, y=-70)
    b = c.create_node("pass", title="BloomPass", x=40, y=-40)
    d = c.create_node("pass", title="Present", x=340, y=-10)
    r = c.create_node("resource", title="SceneColor", x=-280, y=-240)

    c.add_output_socket(r.id, "fbo", "fbo")
    c.add_input_socket(a.id, "input_res", "fbo")
    c.add_output_socket(a.id, "output_res", "fbo")
    c.add_input_socket(b.id, "input_res", "fbo")
    c.add_output_socket(b.id, "output_res", "fbo")
    c.add_input_socket(d.id, "input_res", "fbo")

    c.connect(r.id, "fbo", a.id, "input_res")
    c.connect(a.id, "output_res", b.id, "input_res")
    c.connect(b.id, "output_res", d.id, "input_res")
    c.add_group("Main Viewport", -340, -290, 760, 420)
    return g


def build_ui(graphics) -> UI:
    root = VStack()
    root.preferred_width = pct(100)
    root.preferred_height = pct(100)

    graph = make_demo_graph()
    view = NodeGraphView(graph)
    view.preferred_width = pct(100)
    view.preferred_height = pct(100)
    view.offset_x = 500
    view.offset_y = 330

    root.add_child(view)
    ui = UI(graphics)
    ui.root = root
    return ui


def main():
    window, gl_ctx = create_window("termin-nodegraph demo", 1280, 820)
    try:
        graphics = OpenGLGraphicsBackend.get_instance()
        graphics.ensure_ready()
        glEnable(GL_MULTISAMPLE)
        ui = build_ui(graphics)

        sdl2.SDL_StartTextInput()
        event = sdl2.SDL_Event()
        running = True

        while running:
            while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
                t = event.type
                if t == sdl2.SDL_QUIT:
                    running = False
                    break
                elif t == sdl2.SDL_WINDOWEVENT and event.window.event == video.SDL_WINDOWEVENT_CLOSE:
                    running = False
                    break
                elif t == sdl2.SDL_MOUSEMOTION:
                    ui.mouse_move(float(event.motion.x), float(event.motion.y))
                elif t == sdl2.SDL_MOUSEBUTTONDOWN:
                    ui.mouse_down(
                        float(event.button.x),
                        float(event.button.y),
                        translate_button(event.button.button),
                        translate_mods(sdl2.SDL_GetModState()),
                    )
                elif t == sdl2.SDL_MOUSEBUTTONUP:
                    ui.mouse_up(
                        float(event.button.x),
                        float(event.button.y),
                        translate_button(event.button.button),
                        translate_mods(sdl2.SDL_GetModState()),
                    )
                elif t == sdl2.SDL_MOUSEWHEEL:
                    mx, my = ctypes.c_int(), ctypes.c_int()
                    sdl2.SDL_GetMouseState(ctypes.byref(mx), ctypes.byref(my))
                    ui.mouse_wheel(float(event.wheel.x), float(event.wheel.y), float(mx.value), float(my.value))
                elif t == sdl2.SDL_KEYDOWN:
                    key = translate_key(event.key.keysym.scancode)
                    if key == Key.ESCAPE:
                        running = False
                        break
                    ui.key_down(key, translate_mods(sdl2.SDL_GetModState()))
                elif t == sdl2.SDL_TEXTINPUT:
                    ui.text_input(event.text.text.decode("utf-8"))

            if not running:
                break

            ui.process_deferred()

            w, h = get_drawable_size(window)
            graphics.bind_framebuffer(None)
            graphics.set_viewport(0, 0, w, h)
            graphics.clear_color_depth(0.08, 0.08, 0.10, 1.0)
            ui.render(w, h)
            video.SDL_GL_SwapWindow(window)
    finally:
        video.SDL_GL_DeleteContext(gl_ctx)
        video.SDL_DestroyWindow(window)
        sdl2.SDL_Quit()


if __name__ == "__main__":
    main()
