use std::ffi::c_char;

use autd3capi_driver::*;

use autd3_link_soem::EthernetAdapters;

#[repr(C)]
pub struct EthernetAdaptersPtr(pub *const libc::c_void);

impl_ptr!(EthernetAdaptersPtr, EthernetAdapters);

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDAdapterPointer() -> EthernetAdaptersPtr {
    EthernetAdaptersPtr(Box::into_raw(Box::new(EthernetAdapters::new())) as _)
}

#[no_mangle]
#[must_use]
pub unsafe extern "C" fn AUTDAdapterGetSize(adapters: EthernetAdaptersPtr) -> u32 {
    adapters.len() as u32
}

#[no_mangle]
pub unsafe extern "C" fn AUTDAdapterGetAdapter(
    adapters: EthernetAdaptersPtr,
    idx: u32,
    desc: *mut c_char,
    name: *mut c_char,
) {
    let adapter = &adapters[idx as usize];
    let name_ = std::ffi::CString::new(adapter.name().to_string()).unwrap();
    libc::strcpy(name, name_.as_ptr());
    let desc_ = std::ffi::CString::new(adapter.desc().to_string()).unwrap();
    libc::strcpy(desc, desc_.as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn AUTDAdapterPointerDelete(adapters: EthernetAdaptersPtr) {
    let _ = take!(adapters, EthernetAdapters);
}
