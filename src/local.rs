use std::{
    ffi::{c_char, CStr, CString},
    num::NonZeroUsize,
};

use autd3capi_driver::*;

use autd3_link_soem::{local::ProcessPriority, local::*, SyncMode, ThreadPriority, TimerStrategy};

use crate::{status::Status, thread_priority::ThreadPriorityPtr};

#[no_mangle]
pub unsafe extern "C" fn AUTDLinkSOEMTracingInit() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
}

#[no_mangle]
pub unsafe extern "C" fn AUTDLinkSOEMTracingInitWithFile(path: *const c_char) -> ResultStatus {
    let path = validate_cstr!(path, AUTDStatus, ResultStatus);
    std::fs::File::options()
        .append(true)
        .create(true)
        .open(path)
        .map(|f| {
            tracing_subscriber::fmt()
                .with_writer(f)
                .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
                .with_ansi(false)
                .init();
            AUTDStatus::AUTDTrue
        })
        .into()
}

#[repr(C)]
pub struct SOEMOption {
    pub ifname: *const c_char,
    pub buf_size: u32,
    pub send_cycle: Duration,
    pub sync0_cycle: Duration,
    pub sync_mode: SyncMode,
    pub process_priority: ProcessPriority,
    pub thread_priority: ThreadPriorityPtr,
    pub state_check_interval: Duration,
    pub timer_strategy: TimerStrategy,
    pub sync_tolerance: Duration,
    pub sync_timeout: Duration,
}

impl TryFrom<SOEMOption> for autd3_link_soem::SOEMOption {
    type Error = std::str::Utf8Error;

    fn try_from(value: SOEMOption) -> Result<Self, Self::Error> {
        unsafe {
            let ifname = if value.ifname.is_null() {
                String::new()
            } else {
                std::ffi::CStr::from_ptr(value.ifname).to_str()?.to_string()
            };
            Ok(autd3_link_soem::SOEMOption {
                ifname,
                buf_size: NonZeroUsize::new_unchecked(value.buf_size as _),
                send_cycle: value.send_cycle.into(),
                sync0_cycle: value.sync0_cycle.into(),
                sync_mode: value.sync_mode,
                #[cfg(target_os = "windows")]
                process_priority: value.process_priority,
                thread_priority: *take!(value.thread_priority, ThreadPriority),
                state_check_interval: value.state_check_interval.into(),
                timer_strategy: value.timer_strategy,
                sync_tolerance: value.sync_tolerance.into(),
                sync_timeout: value.sync_timeout.into(),
            })
        }
    }
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEM(
    err_handler: ConstPtr,
    err_context: ConstPtr,
    option: SOEMOption,
) -> ResultLink {
    let out_func = move |slave: usize, status: autd3_link_soem::Status| {
        let (out_f, context) = {
            (
                std::mem::transmute::<ConstPtr, unsafe extern "C" fn(ConstPtr, u32, Status)>(
                    err_handler,
                ),
                err_context,
            )
        };
        out_f(context, slave as _, status.into());
    };
    option
        .try_into()
        .map(|option| SOEM::new(out_func, option))
        .into()
}

#[no_mangle]
#[must_use]
#[allow(unused_variables)]
pub unsafe extern "C" fn AUTDLinkSOEMIsDefault(option: SOEMOption) -> bool {
    option
        .try_into()
        .is_ok_and(|option: autd3_link_soem::SOEMOption| {
            option == autd3_link_soem::SOEMOption::default()
        })
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEMStatusGetMsg(src: Status, dst: *mut c_char) -> u32 {
    let msg = format!("{}", autd3_link_soem::Status::from(src));
    if dst.is_null() {
        return msg.len() as u32 + 1;
    }
    let c_string = CString::new(msg).unwrap();
    let c_str: &CStr = c_string.as_c_str();
    libc::strcpy(dst, c_str.as_ptr());
    0
}
