import base64
import json
import sys
import types


def _install_pure_python_ormsgpack_shim() -> None:
    """
    Provide a pure-Python fallback for `ormsgpack` when Windows Application Control /
    Device Guard blocks unsigned `.pyd` extensions inside `.venv`.
    """
    try:
        import ormsgpack  # noqa: F401
        return
    except ImportError:
        pass

    shim = types.ModuleType("ormsgpack")
    shim.OPT_NON_STR_KEYS = 1
    shim.OPT_SERIALIZE_NUMPY = 2
    shim.OPT_SORT_KEYS = 4

    class MsgpackEncodeError(TypeError):
        pass

    class MsgpackDecodeError(ValueError):
        pass

    def _default_encode(obj):
        if isinstance(obj, (bytes, bytearray)):
            return {"__bytes_b64__": base64.b64encode(bytes(obj)).decode("ascii")}
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise MsgpackEncodeError(f"Object of type {type(obj).__name__} is not serializable")

    def _object_hook(d):
        if len(d) == 1 and "__bytes_b64__" in d:
            return base64.b64decode(d["__bytes_b64__"])
        return d

    def packb(obj, default=None, option=None) -> bytes:
        def fallback(o):
            if default is not None:
                try:
                    return default(o)
                except Exception:
                    pass
            return _default_encode(o)

        return json.dumps(obj, default=fallback).encode("utf-8")

    def unpackb(data, ext_hook=None, option=None):
        if isinstance(data, memoryview):
            data = data.tobytes()
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8")
        return json.loads(data, object_hook=_object_hook)

    shim.MsgpackEncodeError = MsgpackEncodeError
    shim.MsgpackDecodeError = MsgpackDecodeError
    shim.packb = packb
    shim.unpackb = unpackb
    sys.modules["ormsgpack"] = shim


_install_pure_python_ormsgpack_shim()
