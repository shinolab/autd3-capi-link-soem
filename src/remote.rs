use std::{ffi::c_char, net::SocketAddr};

use autd3capi_driver::*;

use autd3_link_soem::remote::link_soem_remote::*;

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDLinkRemoteSOEM(addr: *const c_char) -> ResultSyncLinkBuilder {
    let addr = if addr.is_null() {
        ""
    } else {
        validate_cstr!(addr, SyncLinkBuilderPtr, ResultSyncLinkBuilder)
    };
    addr.parse::<SocketAddr>().map(RemoteSOEM::builder).into()
}
