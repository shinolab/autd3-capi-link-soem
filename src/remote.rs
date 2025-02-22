use std::{ffi::c_char, net::SocketAddr};

use autd3capi_driver::*;

use autd3_link_soem::remote::*;

#[unsafe(no_mangle)]
#[must_use]
pub unsafe extern "C" fn AUTDLinkRemoteSOEM(addr: *const c_char) -> ResultLink {
    let addr = if addr.is_null() {
        ""
    } else {
        validate_cstr!(addr, LinkPtr, ResultLink)
    };
    addr.parse::<SocketAddr>().map(RemoteSOEM::new).into()
}
