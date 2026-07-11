// Test file to determine the correct connection type
use rsfbclient::prelude::*;

fn main() {
    let conn = rsfbclient::builder_native()
        .with_dyn_link()
        .with_remote()
        .host("localhost")
        .port(3050)
        .db_name("test.fdb")
        .user("test")
        .pass("test")
        .connect();
    
    // This will show us the type in the compiler error
    let _: () = conn;
}
