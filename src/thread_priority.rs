use autd3capi_driver::*;

use autd3_link_soem::ThreadPriority;
use thread_priority::ThreadPriorityValue;

#[derive(Clone, Copy)]
#[repr(C)]
pub struct ThreadPriorityPtr(pub *const libc::c_void);

impl From<ThreadPriority> for ThreadPriorityPtr {
    fn from(v: ThreadPriority) -> Self {
        Self(Box::into_raw(Box::new(v)) as _)
    }
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEMThreadPriorityMin() -> ThreadPriorityPtr {
    ThreadPriorityPtr::from(ThreadPriority::Min)
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEMThreadPriorityCrossplatform(value: u8) -> ThreadPriorityPtr {
    ThreadPriorityPtr::from(ThreadPriority::Crossplatform(
        ThreadPriorityValue::try_from(
            value.clamp(ThreadPriorityValue::MIN, ThreadPriorityValue::MAX),
        )
        .unwrap(),
    ))
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEMThreadPriorityMax() -> ThreadPriorityPtr {
    ThreadPriorityPtr::from(ThreadPriority::Max)
}
