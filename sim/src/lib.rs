//! The runtime simulation's hot loops, for `rail_runtime`.
//! Python drives it through the `rail_runtime._sim` module.

pub mod multi;
mod python;
pub mod single;
pub mod train;

#[global_allocator]
static ALLOCATOR: mimalloc::MiMalloc = mimalloc::MiMalloc;

/// mph to m/s.
pub const MPH: f64 = 0.44704;
