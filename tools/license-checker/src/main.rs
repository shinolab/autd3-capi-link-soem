use std::path::Path;

fn main() -> anyhow::Result<()> {
    let changed = autd3_license_check::check(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../Cargo.toml"),
        "ThirdPartyNotice",
        &[],
        &[("SOEM", "SOEM\nhttps://github.com/OpenEtherCATsociety/SOEM")],
    )?;

    if changed {
        return Err(anyhow::anyhow!(
            "Some ThirdPartyNotice.txt files have been updated. Manuall check is required.",
        ));
    }

    Ok(())
}
