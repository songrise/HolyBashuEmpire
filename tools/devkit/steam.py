"""Installed Steamworks adapter, extracted from the proven presentation uploader.

No SDK is loaded on import; target and DLL are supplied by the caller.
"""
import ctypes as C
import os
import time
import struct
U64 = C.c_uint64
U32 = C.c_uint32
PTR = C.c_void_p
BOOL = C.c_bool

class Callback(C.Structure):
    _fields_ = [('user', C.c_int32), ('kind', C.c_int32), ('data', PTR), ('size', C.c_int32)]

class Details(C.Structure):
    _fields_ = [('id', U64), ('result', C.c_int32), ('filetype', C.c_int32), ('creator', U32), ('consumer', U32), ('title', C.c_char * 129), ('description', C.c_char * 8000), ('owner', U64), ('created', U32), ('updated', U32), ('added', U32), ('visibility', C.c_int32), ('banned', BOOL), ('accepted', BOOL), ('tags_truncated', BOOL), ('tags', C.c_char * 1025), ('file_handle', U64), ('preview_handle', U64), ('filename', C.c_char * 260), ('file_size', C.c_int32), ('preview_size', C.c_int32), ('url', C.c_char * 256), ('votes_up', U32), ('votes_down', U32), ('score', C.c_float), ('children', U32)]

class Steam:

    def __init__(self, dll, app_id, item_id):
        self.app_id = int(app_id)
        self.item_id = int(item_id)
        APP = self.app_id
        os.environ['SteamAppId'] = str(APP)
        os.environ['SteamGameId'] = str(APP)
        self.dll = C.CDLL(str(dll))

        def f(name, result, *args):
            fn = getattr(self.dll, 'SteamAPI_' + name)
            fn.restype = result
            fn.argtypes = list(args)
            return fn
        self.f = f
        self.shutdown = f('Shutdown', None)
        if not f('Init', BOOL)():
            raise RuntimeError('Steam API init failed; no publication was attempted.')
        self.ugc = f('SteamUGC_v016', PTR)()
        self.utils = f('SteamUtils_v010', PTR)()
        self.user = f('SteamUser_v021', PTR)()
        if not (self.ugc and self.utils and self.user):
            raise RuntimeError('Steam API operation failed')
        if not f('ISteamUtils_GetAppID', U32, PTR)(self.utils) == APP:
            raise RuntimeError('Steam API operation failed')
        self.owner = f('ISteamUser_GetSteamID', U64, PTR)(self.user)
        f('ManualDispatch_Init', None)()
        self.pipe = f('GetHSteamPipe', C.c_int32)()
        self.frame = f('ManualDispatch_RunFrame', None, C.c_int32)
        self.next = f('ManualDispatch_GetNextCallback', BOOL, C.c_int32, C.POINTER(Callback))
        self.free = f('ManualDispatch_FreeLastCallback', None, C.c_int32)
        self.result = f('ManualDispatch_GetAPICallResult', BOOL, C.c_int32, U64, PTR, C.c_int32, C.c_int32, C.POINTER(BOOL))

    def wait(self, call, timeout=50):
        if not call:
            raise RuntimeError('Steam returned an invalid async call.')
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.frame(self.pipe)
            msg = Callback()
            while self.next(self.pipe, C.byref(msg)):
                try:
                    if msg.kind == 703:
                        if msg.size < 16:
                            raise RuntimeError('Truncated Steam callback')
                        completed, kind, size = struct.unpack_from('<QII', C.string_at(msg.data, msg.size))
                        if completed == call:
                            if not 1 <= size <= 1024 * 1024:
                                raise RuntimeError('Invalid Steam result size')
                            payload = C.create_string_buffer(size)
                            failed = BOOL()
                            if not self.result(self.pipe, call, payload, size, kind, C.byref(failed)) or failed.value:
                                raise RuntimeError('Steam async result failed.')
                            return (kind, bytes(payload))
                finally:
                    self.free(self.pipe)
            time.sleep(0.1)
        raise TimeoutError('Steam operation did not complete; query before retrying publication.')

    def query(self, language=None):
        ITEM = self.item_id
        APP = self.app_id
        ids = (U64 * 1)(ITEM)
        q = self.f('ISteamUGC_CreateQueryUGCDetailsRequest', U64, PTR, C.POINTER(U64), U32)(self.ugc, ids, 1)
        if not (q and q != 2 ** 64 - 1):
            raise RuntimeError('Steam API operation failed')
        if language:
            if not self.f('ISteamUGC_SetLanguage', BOOL, PTR, U64, C.c_char_p)(self.ugc, q, language.encode('ascii')):
                raise RuntimeError('Steam API operation failed')
        if not self.f('ISteamUGC_SetReturnAdditionalPreviews', BOOL, PTR, U64, BOOL)(self.ugc, q, True):
            raise RuntimeError('Steam API operation failed')
        if not self.f('ISteamUGC_SetReturnLongDescription', BOOL, PTR, U64, BOOL)(self.ugc, q, True):
            raise RuntimeError('Steam API operation failed')
        if not self.f('ISteamUGC_SetReturnMetadata', BOOL, PTR, U64, BOOL)(self.ugc, q, True):
            raise RuntimeError('Steam API operation failed')
        cache = self.f('ISteamUGC_SetAllowCachedResponse', BOOL, PTR, U64, U32)
        if not cache(self.ugc, q, 0):
            raise RuntimeError('Steam API operation failed')
        try:
            kind, result = self.wait(self.f('ISteamUGC_SendQueryUGCRequest', U64, PTR, U64)(self.ugc, q))
            if not (struct.unpack_from('<i', result, 8)[0] == 1 and struct.unpack_from('<I', result, 12)[0] == 1):
                raise RuntimeError('Steam API operation failed')
            d = Details()
            if not self.f('ISteamUGC_GetQueryUGCResult', BOOL, PTR, U64, U32, C.POINTER(Details))(self.ugc, q, 0, C.byref(d)):
                raise RuntimeError('Steam API operation failed')
            if not (d.id == ITEM and d.consumer == APP and (d.result == 1)):
                raise RuntimeError('Steam API operation failed')
            if not d.owner == self.owner:
                raise RuntimeError('This item is not owned by the signed-in Steam account.')
            count = self.f('ISteamUGC_GetQueryUGCNumAdditionalPreviews', U32, PTR, U64, U32)(self.ugc, q, 0)
            items = []
            for i in range(count):
                url = C.create_string_buffer(4096)
                name = C.create_string_buffer(1024)
                t = C.c_int32()
                if not self.f('ISteamUGC_GetQueryUGCAdditionalPreview', BOOL, PTR, U64, U32, U32, PTR, U32, PTR, U32, C.POINTER(C.c_int32))(self.ugc, q, 0, i, url, 4096, name, 1024, C.byref(t)):
                    raise RuntimeError('Steam API operation failed')
                items.append(dict(index=i, url=url.value.decode('utf-8'), filename=name.value.decode('utf-8'), type=t.value))
            preview = C.create_string_buffer(4096)
            if not self.f('ISteamUGC_GetQueryUGCPreviewURL', BOOL, PTR, U64, U32, PTR, U32)(self.ugc, q, 0, preview, 4096):
                raise RuntimeError('Steam API operation failed')
            metadata = C.create_string_buffer(4096)
            self.f('ISteamUGC_GetQueryUGCMetadata', BOOL, PTR, U64, U32, PTR, U32)(self.ugc, q, 0, metadata, 4096)
            record = dict(item_id=ITEM, app_id=APP, title=d.title.decode('utf-8'), description=d.description.decode('utf-8'), visibility=d.visibility, preview_url=preview.value.decode('utf-8'), additional_previews=items, metadata=metadata.value.decode('utf-8'), file_size=d.file_size, updated=d.updated, language=language or 'english')
            return record
        finally:
            self.f('ISteamUGC_ReleaseQueryUGCRequest', BOOL, PTR, U64)(self.ugc, q)

    def submit(self, *, content=None, description=None, language=None, metadata=None, note):
        """Only named fields can change; gallery/title/visibility have no setter here."""
        if bool(description is not None) != bool(language):
            raise ValueError('Description and language must be supplied together')
        if content is None and description is None:
            raise ValueError('Empty Workshop operation')
        if metadata is not None and len(metadata.encode('utf-8')) >= 4096:
            raise ValueError('Steam metadata exceeds the supported buffer')
        handle = self.f('ISteamUGC_StartItemUpdate', U64, PTR, U32, U64)(self.ugc, self.app_id, self.item_id)
        if not handle or handle == 2**64 - 1:
            raise RuntimeError('Steam refused the update handle')
        def set_string(name, value):
            if not self.f(name, BOOL, PTR, U64, C.c_char_p)(self.ugc, handle, value.encode('utf-8')):
                raise RuntimeError('Steam rejected ' + name)
        if content is not None:
            set_string('ISteamUGC_SetItemContent', content)
        if metadata is not None:
            set_string('ISteamUGC_SetItemMetadata', metadata)
        if description is not None:
            set_string('ISteamUGC_SetItemUpdateLanguage', language)
            set_string('ISteamUGC_SetItemDescription', description)
        _, payload = self.wait(self.f('ISteamUGC_SubmitItemUpdate', U64, PTR, U64, C.c_char_p)(
            self.ugc, handle, note.encode('utf-8')))
        if len(payload) < 5:
            raise RuntimeError('Truncated Steam update result')
        result = struct.unpack_from('<i', payload)[0]
        if result != 1:
            raise RuntimeError(f'Steam update returned {result}')
        if payload[4]:
            raise RuntimeError('Steam requires the user to accept Workshop legal terms')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.shutdown()
