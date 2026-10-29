//! Many trains at once, stepped by time, with a DC third-rail network solve.
//!
//! Each service runs on its own track at a fixed headway with one stopping pattern.
//! Braking trains regenerate into the third rail; substations are diode rectifiers and can't absorb it,
//! so regen only helps other trains, and a train sheds regen to keep its voltage at or below `V_REGEN_MAX`.

use crate::MPH;
use crate::train::{Supply, Train, V_MIN, V0};

/// Time step, s.
pub const DT: f64 = 0.5;
/// Wheel to line.
pub const REGEN_EFF: f64 = 0.80;
/// A braking train sheds regen to stay at or below this, V.
pub const V_REGEN_MAX: f64 = 900.0;
/// Conductance holding a braking train at `V_REGEN_MAX`, S: stiff enough that it sits within millivolts,
/// so it can't stay held well below the limit.
const G_HOLD: f64 = 1e6;
/// Contact rail, Ω per mile: about 150 lb/yd of steel.
pub const R_CONTACT: f64 = 0.020;
pub const MILE: f64 = 1609.34;
/// Dwell at each intermediate stop, s.
pub const DWELL: f64 = 30.0;

/// Trains on one stopping pattern in one direction, on their own track.
#[derive(Clone, Debug)]
pub struct Service {
    /// Stops, as chainage from Penn, m.
    pub stops: Vec<f64>,
    pub inbound: bool,
    pub track: usize,
    /// s.
    pub headway: f64,
    /// First departure, s.
    pub offset: f64,
}

/// One simulation: a train type running `services` on a line for `horizon` s.
#[derive(Clone, Debug)]
pub struct Job {
    pub train: Train,
    /// Speed limits by sample, mph, in chainage order.
    pub lim_mph: Vec<f64>,
    /// Sample spacing, m.
    pub ds: f64,
    /// Chainage of the last sample, m.
    pub s_end: f64,
    /// Substation chainages, m.
    pub subs: Vec<f64>,
    /// Substation source resistances, ohm.
    pub r_subs: Vec<f64>,
    /// Running-rail return resistance from chainage 0 to each sample, Ω,
    /// with every parallel track's running rails bonded together.
    pub r_return: Vec<f64>,
    pub services: Vec<Service>,
    pub horizon: f64,
    pub regen: bool,
    /// Run only the first train to depart, alone.
    pub single: bool,
}

/// A train that reached its last stop.
#[derive(Clone, Debug, PartialEq)]
pub struct Finished {
    /// Index into the job's services.
    pub service: usize,
    /// Departure, s.
    pub t0: f64,
    /// Arrival, s.
    pub done: f64,
}

#[derive(Clone, Debug)]
pub struct Outcome {
    /// In departure order.
    pub finished: Vec<Finished>,
    /// Lowest train voltage over the run, V; `None` off third rail.
    pub vmin: Option<f64>,
    /// Steps whose network solve didn't converge.
    pub nonconverged: u32,
}

/// One service's pattern in its own direction: limits and braking envelope by distance travelled.
struct Run {
    /// Limit, m/s.
    lim: Vec<f64>,
    /// `lim`, lowered so the train can brake for every stop and restriction.
    env: Vec<f64>,
    /// Stops, as distance travelled, m.
    stops: Vec<f64>,
    ds: f64,
    s_end: f64,
    inbound: bool,
}

impl Run {
    fn new(job: &Job, sv: &Service) -> Self {
        let mut lim: Vec<f64> = job.lim_mph.iter().map(|x| x * MPH).collect();
        if sv.inbound {
            lim.reverse();
        }
        let mut stops: Vec<f64> = sv
            .stops
            .iter()
            .map(|&x| if sv.inbound { job.s_end - x } else { x })
            .collect();
        stops.sort_by(f64::total_cmp);
        let mut env = lim.clone();
        for &sp in &stops {
            env[(sp / job.ds).round_ties_even() as usize] = 0.0;
        }
        for i in (0..env.len() - 1).rev() {
            env[i] = env[i].min((env[i + 1] * env[i + 1] + 2.0 * job.train.brake * job.ds).sqrt());
        }
        Run {
            lim,
            env,
            stops,
            ds: job.ds,
            s_end: job.s_end,
            inbound: sv.inbound,
        }
    }

    /// Track chainage (from Penn) for distance travelled `p`.
    fn chain(&self, p: f64) -> f64 {
        if self.inbound { self.s_end - p } else { p }
    }

    /// Sample index at distance travelled `p`.
    fn at(&self, p: f64) -> usize {
        ((p / self.ds) as usize).min(self.env.len() - 1)
    }
}

struct Car {
    run: usize,
    track: usize,
    p: f64,
    v: f64,
    dwell: f64,
    t0: f64,
    next_stop: usize,
    done: Option<f64>,
    /// Contact- and running-rail voltages at the last step's solve, to start the next one from.
    v_contact: f64,
    v_return: f64,
}

/// Electrical power the train wants this step, W (negative when regenerating).
fn demand(train: &Train, car: &Car, r: &Run, regen: bool) -> f64 {
    if car.dwell > 0.0 {
        return train.aux;
    }
    let i = r.at(car.p);
    let j = r.at(car.p + car.v * DT);
    let want = r.env[(i + 1).min(r.env.len() - 1)].min(r.lim[i]);
    let v = car.v.max(0.1);
    if car.v < want - 0.05 {
        return (train.f_max * v).min(train.p_shaft) / 0.90 + train.aux;
    }
    if r.env[j] < car.v - 0.05 {
        // Braking: the electric brake recovers what it can, up to rated power.
        let rec = if regen {
            (train.m_eff * train.brake * car.v).min(train.p_shaft) * REGEN_EFF
        } else {
            0.0
        };
        return train.aux - rec;
    }
    train.resist(car.v) * car.v / 0.90 + train.aux // cruise
}

/// Solve `g x = b` in place, where `g` is row-major `n` × `n` with nonzeros only within `kb` of the diagonal.
/// No pivoting: a nodal conductance matrix is diagonally dominant.
fn solve_banded(g: &mut [f64], b: &mut [f64], n: usize, kb: usize) {
    for c in 0..n {
        let d = g[c * n + c];
        let end = (c + kb + 1).min(n);
        for r in c + 1..end {
            let f = g[r * n + c] / d;
            if f != 0.0 {
                for k in c..end {
                    g[r * n + k] -= f * g[c * n + k];
                }
                b[r] -= f * b[c];
            }
        }
    }
    for c in (0..n).rev() {
        let end = (c + kb + 1).min(n);
        let s: f64 = (c + 1..end).map(|k| g[c * n + k] * b[k]).sum();
        b[c] = (b[c] - s) / g[c * n + c];
    }
}

/// Current a car not held at `V_REGEN_MAX` draws at voltage `vt` (negative when regenerating),
/// and its slope, A/V, for Newton's method.
fn draw(train: &Train, dem: f64, vt: f64) -> (f64, f64) {
    if dem < 0.0 {
        let i = dem / vt;
        return if i < -train.i_max {
            (-train.i_max, 0.0)
        } else {
            (i, -i / vt)
        };
    }
    let (i, di) = if dem / vt > train.i_max {
        (train.i_max, 0.0)
    } else {
        (dem / vt, -dem / (vt * vt))
    };
    if vt >= V_MIN {
        return (i, di);
    }
    // Shed load as voltage collapses.
    let s = (vt - 0.6 * V_MIN) / (0.4 * V_MIN);
    if s <= 0.0 {
        return (0.0, 0.0);
    }
    (i * s, di * s + i / (0.4 * V_MIN))
}

/// Running-rail return resistance from chainage 0 to `x`, Ω, carried on linearly past either end.
fn r_return(job: &Job, x: f64) -> f64 {
    let r = &job.r_return;
    let k = ((x / job.ds).floor() as isize).clamp(0, r.len() as isize - 2) as usize;
    r[k] + (r[k + 1] - r[k]) * (x / job.ds - k as f64)
}

/// Nodal solve of the DC network: power delivered to each active car, W, and the node voltages.
/// Returns whether the voltage iteration converged.
/// The iteration starts from the last step's voltages, `v_subs` and each car's own,
/// since trains move little in one step.
///
/// Nodes are each substation's positive bus, which every track's contact rail meets,
/// then each car's contact-rail node, then each car's running-rail node.
/// Contact rails run per track; the running rails of every track are bonded into one return,
/// grounded at each substation's negative.
fn solve(
    job: &Job,
    cars: &[&Car],
    runs: &[Run],
    dem: &[f64],
    train: &Train,
    n_tracks: usize,
    v_subs: &[f64],
) -> (Vec<f64>, Vec<f64>, bool) {
    let subs = &job.subs;
    let n_sub = subs.len();
    let n_car = cars.len();
    let n = n_sub + 2 * n_car;
    let contact = |j: usize| n_sub + j;
    let ret = |j: usize| n_sub + n_car + j;
    let pos: Vec<f64> = cars.iter().map(|c| runs[c.run].chain(c.p)).collect();
    // The matrix is laid out with nodes in chainage order, so every link is between nearby rows,
    // and `kb` is the farthest any link reaches from the diagonal.
    let mut order: Vec<(f64, usize)> = subs.iter().copied().zip(0..).collect();
    order.extend((0..n_car).flat_map(|j| [(pos[j], contact(j)), (pos[j], ret(j))]));
    order.sort_by(|x, y| x.0.total_cmp(&y.0).then(x.1.cmp(&y.1)));
    let mut slot = vec![0; n];
    for (i, &(_, node)) in order.iter().enumerate() {
        slot[node] = i;
    }
    let mut kb = 0;
    // Branch conductances only depend on positions.
    let mut g0 = vec![0.0; n * n];
    let mut link = |g0: &mut Vec<f64>, a: Option<usize>, b: Option<usize>, r: f64| {
        let g = 1.0 / r.max(1e-6);
        let (a, b) = (a.map(|x| slot[x]), b.map(|x| slot[x]));
        if let (Some(a), Some(b)) = (a, b) {
            kb = kb.max(a.abs_diff(b));
        }
        for (x, y) in [(a, b), (b, a)] {
            if let Some(x) = x {
                g0[x * n + x] += g;
                if let Some(y) = y {
                    g0[x * n + y] -= g;
                }
            }
        }
    };
    for track in 0..n_tracks {
        let mut nodes: Vec<(f64, usize)> = subs.iter().copied().zip(0..).collect();
        nodes.extend(
            (0..n_car)
                .filter(|&j| cars[j].track == track)
                .map(|j| (pos[j], contact(j))),
        );
        nodes.sort_by(|x, y| x.0.total_cmp(&y.0).then(x.1.cmp(&y.1)));
        for w in nodes.windows(2) {
            let ((xa, a), (xb, b)) = (w[0], w[1]);
            link(&mut g0, Some(a), Some(b), (xb - xa) / MILE * R_CONTACT);
        }
    }
    // The bonded return: substations are ground (None), cars their running-rail nodes.
    let mut nodes: Vec<(f64, Option<usize>)> = subs.iter().map(|&x| (x, None)).collect();
    nodes.extend((0..n_car).map(|j| (pos[j], Some(ret(j)))));
    nodes.sort_by(|x, y| x.0.total_cmp(&y.0));
    for w in nodes.windows(2) {
        let ((xa, a), (xb, b)) = (w[0], w[1]);
        if a.is_some() || b.is_some() {
            link(&mut g0, a, b, r_return(job, xb) - r_return(job, xa));
        }
    }
    // Starting no higher than `V0` starts every rectifier conducting;
    // starting from a step whose regen floated the network over it would leave them blocking
    // and let Newton's method settle at the clamp with a train drawing power.
    let mut v = vec![0.0; n];
    for (x, &vs) in v.iter_mut().zip(v_subs) {
        *x = vs.min(V0);
    }
    for (j, c) in cars.iter().enumerate() {
        v[ret(j)] = c.v_return;
        v[contact(j)] = c.v_return + (c.v_contact - c.v_return).min(V0);
    }
    let mut cur = vec![0.0; n_car];
    // Braking trains held at `V_REGEN_MAX`, returning only the regen the line takes there,
    // the rest going to the friction brake.
    // Which are held is settled by the voltages alone, so the solve has one answer whatever it starts from.
    let mut held = vec![false; n_car];
    let mut converged = false;
    let (mut g, mut b, mut bs) = (vec![0.0; n * n], vec![0.0; n], vec![0.0; n]);
    for it in 0..200 {
        let mut changed = false;
        g.copy_from_slice(&g0);
        b.fill(0.0);
        for k in 0..n_sub {
            // Diode rectifier: conducts only outward (a tiny leak keeps the network grounded).
            let gk = if v[k] <= V0 + 1e-6 {
                1.0 / job.r_subs[k]
            } else {
                1e-6
            };
            g[slot[k] * n + slot[k]] += gk;
            b[k] += V0 * gk;
        }
        for j in (0..n_car).filter(|&j| dem[j] < 0.0) {
            let vt = (v[contact(j)] - v[ret(j)]).max(1.0);
            let full = (dem[j] / vt).max(-train.i_max);
            // Release a hold that took more than full regen or drew from the line; hold a train over the limit.
            let hold = if held[j] {
                cur[j] > full && cur[j] < 0.0 || vt > V_REGEN_MAX
            } else {
                vt > V_REGEN_MAX
            };
            changed |= hold != held[j];
            held[j] = hold;
        }
        for j in 0..n_car {
            let vt = (v[contact(j)] - v[ret(j)]).max(1.0);
            // Each car is linearized about `vt` for Newton's method, as a conductance `gd` across it
            // in parallel with a current source `i0`; a held car is a stiff source at `V_REGEN_MAX`.
            let (gd, i0) = if held[j] {
                (G_HOLD, -G_HOLD * V_REGEN_MAX)
            } else {
                // A load's negative slope would make it a source when every rectifier blocks,
                // so only a positive slope is linearized.
                let (i, di) = draw(train, dem[j], vt);
                let di = di.max(0.0);
                cur[j] = i;
                (di, i - di * vt)
            };
            let (c, r) = (slot[contact(j)], slot[ret(j)]);
            g[c * n + c] += gd;
            g[r * n + r] += gd;
            g[c * n + r] -= gd;
            g[r * n + c] -= gd;
            b[contact(j)] -= i0;
            b[ret(j)] += i0;
        }
        for (i, &x) in b.iter().enumerate() {
            bs[slot[i]] = x;
        }
        solve_banded(&mut g, &mut bs, n, kb);
        for (i, x) in b.iter_mut().enumerate() {
            *x = bs[slot[i]];
        }
        // A held train returns what its hold passes, within its full regen;
        // past either end, the next iteration releases it.
        // Every other car draws what it does at the new voltage.
        for j in 0..n_car {
            let vt = (b[contact(j)] - b[ret(j)]).max(1.0);
            cur[j] = if held[j] {
                let full = (dem[j] / vt).max(-train.i_max);
                (-G_HOLD * (V_REGEN_MAX - vt)).clamp(full, 0.0)
            } else {
                draw(train, dem[j], vt).0
            };
        }
        // Clamp to the physical range: below 0.6 V_MIN trains draw nothing, above V_REGEN_MAX they shed regen.
        // With every rectifier blocking, the positive side floats, so substation buses are clamped too.
        for x in &mut b[..n_sub] {
            *x = x.clamp(0.6 * V_MIN, V_REGEN_MAX + 50.0);
        }
        for j in 0..n_car {
            let vr = b[ret(j)];
            b[contact(j)] = vr + (b[contact(j)] - vr).clamp(0.6 * V_MIN, V_REGEN_MAX + 50.0);
        }
        let diff = v
            .iter()
            .zip(&b)
            .map(|(a, c)| (a - c).abs())
            .fold(0.0, f64::max);
        // Tight, since the lowest voltage of a busy run hangs on exactly when trains meet,
        // which a looser one shifts; Newton's method gets there in a few more iterations.
        if diff < 1e-6 && !changed {
            v.copy_from_slice(&b);
            converged = true;
            break;
        }
        // Full Newton steps; if the rectifiers' and holds' states ever cycle instead of settling,
        // damped steps after 20 iterations break the cycle.
        let step = if it < 20 { 1.0 } else { 0.3 };
        for (a, c) in v.iter_mut().zip(&b) {
            *a += step * (c - *a);
        }
    }
    let power = (0..n_car)
        .map(|j| (v[contact(j)] - v[ret(j)]) * cur[j])
        .collect();
    (power, v, converged)
}

pub fn simulate(job: &Job) -> Outcome {
    let train = &job.train;
    let runs: Vec<Run> = job.services.iter().map(|sv| Run::new(job, sv)).collect();
    let n_tracks = job
        .services
        .iter()
        .map(|sv| sv.track)
        .max()
        .map_or(0, |t| t + 1);
    let mut cars: Vec<Car> = Vec::new();
    let mut vmin: Option<f64> = None;
    let mut nonconverged = 0;
    let mut v_subs = vec![V0; job.subs.len()];
    let mut next_dep: Vec<f64> = job.services.iter().map(|sv| sv.offset).collect();
    let mut t = 0.0;
    while t < job.horizon {
        for (i, sv) in job.services.iter().enumerate() {
            if t >= next_dep[i] && !(job.single && !cars.is_empty()) {
                cars.push(Car {
                    run: i,
                    track: sv.track,
                    p: runs[i].stops[0],
                    v: 0.0,
                    dwell: 0.0,
                    t0: t,
                    next_stop: 1,
                    done: None,
                    v_contact: V0,
                    v_return: 0.0,
                });
                next_dep[i] += sv.headway;
            }
        }
        let active: Vec<usize> = (0..cars.len())
            .filter(|&k| cars[k].done.is_none())
            .collect();
        if job.single && !cars.is_empty() && active.is_empty() {
            break;
        }
        let dem: Vec<f64> = active
            .iter()
            .map(|&k| demand(train, &cars[k], &runs[cars[k].run], job.regen))
            .collect();
        let power = if train.supply == Supply::ThirdRail {
            let refs: Vec<&Car> = active.iter().map(|&k| &cars[k]).collect();
            let (power, v, converged) = solve(job, &refs, &runs, &dem, train, n_tracks, &v_subs);
            if !converged && !refs.is_empty() {
                nonconverged += 1;
            }
            let n_sub = v_subs.len();
            v_subs.copy_from_slice(&v[..n_sub]);
            for (j, &k) in active.iter().enumerate() {
                let c = &mut cars[k];
                c.v_contact = v[n_sub + j];
                c.v_return = v[n_sub + active.len() + j];
                let lo = c.v_contact - c.v_return;
                vmin = Some(vmin.map_or(lo, |m| m.min(lo)));
            }
            power
        } else {
            dem
        };
        for (&k, pe) in active.iter().zip(power) {
            let c = &mut cars[k];
            let r = &runs[c.run];
            if c.dwell > 0.0 {
                c.dwell -= DT;
                continue;
            }
            let i = r.at(c.p);
            let u = c.v.max(0.1);
            let mech = (pe - train.aux).max(0.0) * 0.90;
            let acc = (train.f_max.min(mech / u) - train.resist(c.v)) / train.m_eff;
            let mut v_new = (c.v + acc * DT).max(0.0);
            let j = r.at(c.p + c.v * DT);
            v_new = v_new.min(r.env[j]).min(r.lim[i]);
            let stop = r.stops[c.next_stop];
            if stop - c.p > 1.0 {
                v_new = v_new.max(1.0f64.min((2.0 * train.brake * (stop - c.p).max(0.0)).sqrt()));
            }
            c.p += (c.v + v_new) / 2.0 * DT;
            c.v = v_new;
            if c.p >= stop - 1.0 {
                c.p = stop;
                c.v = 0.0;
                if c.next_stop == r.stops.len() - 1 {
                    c.done = Some(t);
                } else {
                    c.dwell = DWELL;
                    c.next_stop += 1;
                }
            }
        }
        t += DT;
    }
    let finished = cars
        .iter()
        .filter_map(|c| {
            c.done.map(|done| Finished {
                service: c.run,
                t0: c.t0,
                done,
            })
        })
        .collect();
    Outcome {
        finished,
        vmin,
        nonconverged,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn solves_banded_systems() {
        let mut g = vec![2.0, 1.0, 0.0, 1.0, 3.0, 1.0, 0.0, 1.0, 4.0];
        let mut b = vec![3.0, 5.0, 5.0];
        solve_banded(&mut g, &mut b, 3, 1);
        for (x, want) in b.iter().zip([1.0, 1.0, 1.0]) {
            assert!((x - want).abs() < 1e-12, "{b:?}");
        }
    }

    fn train(supply: Supply) -> Train {
        let m = (5.0 * 115.0 + 10.0 * 105.0 * 0.080) * 1000.0;
        Train {
            m,
            m_eff: m * 1.08,
            p_shaft: 8e6,
            f_max: m * 1.08 * 2.0 * MPH,
            cars: 10.0,
            supply,
            brake: 2.0 * MPH,
            aux: 300e3,
            i_max: (8e6 / 0.9 + 300e3) / V0,
            sharing: 1.0,
        }
    }

    fn job(supply: Supply, single: bool) -> Job {
        let n = 3201; // 16 km at 5 m
        Job {
            train: train(supply),
            lim_mph: vec![80.0; n],
            ds: 5.0,
            s_end: 16_000.0,
            subs: (0..=4).map(|k| k as f64 * 4000.0).collect(),
            r_subs: vec![0.010; 5],
            r_return: (0..n).map(|k| k as f64 * 5.0 / MILE * 0.020).collect(),
            services: vec![
                Service {
                    stops: vec![0.0, 8000.0, 15_900.0],
                    inbound: true,
                    track: 0,
                    headway: 120.0,
                    offset: 0.0,
                },
                Service {
                    stops: vec![0.0, 8000.0, 15_900.0],
                    inbound: false,
                    track: 1,
                    headway: 120.0,
                    offset: 60.0,
                },
            ],
            horizon: 3600.0,
            regen: true,
            single,
        }
    }

    /// Busy third rail drops voltage, so trains run slower than a lone train; 25 kV doesn't.
    #[test]
    fn busy_third_rail_is_slower() {
        let mean = |o: &Outcome| {
            let xs: Vec<f64> = o
                .finished
                .iter()
                .filter(|f| f.t0 >= 1200.0)
                .map(|f| f.done - f.t0)
                .collect();
            xs.iter().sum::<f64>() / xs.len() as f64
        };
        let one = simulate(&job(Supply::ThirdRail, true));
        assert_eq!(one.finished.len(), 1);
        let lone = one.finished[0].done - one.finished[0].t0;
        let busy = simulate(&job(Supply::ThirdRail, false));
        assert!(mean(&busy) > lone, "{} vs {lone}", mean(&busy));
        assert!(busy.vmin.unwrap() < V0 - 50.0);
        assert_eq!(busy.nonconverged, 0);
        let ac = simulate(&job(Supply::Ac, false));
        assert!(ac.vmin.is_none());
        assert!(mean(&ac) < mean(&busy));
    }
}
