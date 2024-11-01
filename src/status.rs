#[repr(u8)]
pub enum Status {
    Error = 0,
    StateChanged = 1,
    Lost = 2,
}

impl From<Status> for autd3_link_soem::Status {
    fn from(value: Status) -> Self {
        match value {
            Status::Error => autd3_link_soem::Status::Error,
            Status::StateChanged => autd3_link_soem::Status::StateChanged,
            Status::Lost => autd3_link_soem::Status::Lost,
        }
    }
}

impl From<autd3_link_soem::Status> for Status {
    fn from(value: autd3_link_soem::Status) -> Self {
        match value {
            autd3_link_soem::Status::Error => Status::Error,
            autd3_link_soem::Status::StateChanged => Status::StateChanged,
            autd3_link_soem::Status::Lost => Status::Lost,
        }
    }
}
