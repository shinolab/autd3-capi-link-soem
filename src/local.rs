use std::{
    convert::Infallible,
    ffi::{c_char, CStr, CString},
    num::NonZeroUsize,
    time::Duration,
};

use autd3capi_driver::*;

use autd3_link_soem::{
    local::link_soem::*, local::ProcessPriority, SyncMode, ThreadPriority, TimerStrategy,
};

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

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEM(
    ifname: *const c_char,
    buf_size: u32,
    send_cycle_ns: u64,
    sync0_cycle_ns: u64,
    err_handler: ConstPtr,
    err_context: ConstPtr,
    mode: SyncMode,
    process_priority: ProcessPriority,
    thread_priority: ThreadPriorityPtr,
    state_check_interval_ns: u64,
    timer_strategy: TimerStrategy,
    tolerance_ns: u64,
    sync_timeout_ns: u64,
) -> ResultSyncLinkBuilder {
    let ifname = if ifname.is_null() {
        ""
    } else {
        validate_cstr!(ifname, SyncLinkBuilderPtr, ResultSyncLinkBuilder)
    };
    let builder = SOEM::builder()
        .with_ifname(ifname)
        .with_buf_size(NonZeroUsize::new_unchecked(buf_size as _))
        .with_send_cycle(Duration::from_nanos(send_cycle_ns))
        .with_sync0_cycle(Duration::from_nanos(sync0_cycle_ns))
        .with_sync_mode(mode)
        .with_thread_priority(*take!(thread_priority, ThreadPriority))
        .with_state_check_interval(Duration::from_nanos(state_check_interval_ns))
        .with_timer_strategy(timer_strategy)
        .with_sync_tolerance(std::time::Duration::from_nanos(tolerance_ns))
        .with_sync_timeout(std::time::Duration::from_nanos(sync_timeout_ns));
    let builder = if err_handler.0.is_null() {
        builder
    } else {
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
        builder.with_err_handler(out_func)
    };
    #[cfg(target_os = "windows")]
    let builder = builder.with_process_priority(process_priority);
    #[cfg(not(target_os = "windows"))]
    let _ = process_priority;
    Result::<_, Infallible>::Ok(builder).into()
}

#[no_mangle]
#[must_use]
#[allow(unused_variables)]
pub unsafe extern "C" fn AUTDLinkSOEMIsDefault(
    buf_size: u32,
    send_cycle_ns: u64,
    sync0_cycle_ns: u64,
    mode: SyncMode,
    process_priority: ProcessPriority,
    thread_priority: ThreadPriorityPtr,
    state_check_interval_ns: u64,
    timer_strategy: TimerStrategy,
    tolerance_ns: u64,
    sync_timeout_ns: u64,
) -> bool {
    let default = SOEM::builder();
    let res = buf_size as usize == default.buf_size().get()
        && send_cycle_ns as u128 == default.send_cycle().as_nanos()
        && sync0_cycle_ns as u128 == default.sync0_cycle().as_nanos()
        && mode == default.sync_mode()
        && *take!(thread_priority, ThreadPriority) == default.thread_priority()
        && state_check_interval_ns as u128 == default.state_check_interval().as_nanos()
        && timer_strategy == default.timer_strategy()
        && tolerance_ns as u128 == default.sync_tolerance().as_nanos()
        && sync_timeout_ns as u128 == default.sync_timeout().as_nanos();
    #[cfg(target_os = "windows")]
    let res = res && process_priority == default.process_priority();
    res
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkSOEMStatusGetMsg(src: Status, dst: *mut c_char) -> u32 {
    let msg = format!("{}", autd3_link_soem::Status::from(src));
    if dst.is_null() {
        return msg.as_bytes().len() as u32 + 1;
    }
    let c_string = CString::new(msg).unwrap();
    let c_str: &CStr = c_string.as_c_str();
    libc::strcpy(dst, c_str.as_ptr());
    0
}
