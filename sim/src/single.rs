//! One train alone between two stops, stepped by distance.

use crate::MPH;
use crate::train::Train;

/// Seconds from standing at the first sample to standing at the last,
/// under `lim_mph`, fed through `r_eff` ohms (NaN under catenary), with samples `ds` m apart.
pub fn run(train: &Train, lim_mph: &[f64], r_eff: &[f64], ds: f64) -> f64 {
    let n = lim_mph.len();
    assert_eq!(n, r_eff.len());
    assert!(n >= 2);
    let mut vl: Vec<f64> = lim_mph.iter().map(|x| x * MPH).collect();
    // Stand at both stations.
    vl[0] = 0.0;
    vl[n - 1] = 0.0;
    let p: Vec<f64> = r_eff.iter().map(|&r| train.power(r)).collect();
    let mut v = vl.clone();
    for i in 1..n {
        let u = v[i - 1].max(0.1);
        let f = train.f_max.min(p[i - 1] / u);
        let acc = (f - train.resist(u)) / train.m_eff;
        v[i] = vl[i].min((v[i - 1] * v[i - 1] + 2.0 * acc * ds).max(0.0).sqrt());
    }
    for i in (0..n - 1).rev() {
        v[i] = v[i].min((v[i + 1] * v[i + 1] + 2.0 * train.brake * ds).sqrt());
    }
    v.windows(2)
        .map(|w| ds / ((w[0] + w[1]) / 2.0).max(0.3))
        .sum()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::train::Supply;

    fn m8() -> Train {
        let m = (5.0 * 129.2 + 10.0 * 105.0 * 0.080) * 1000.0;
        Train {
            m,
            m_eff: m * 1.08,
            p_shaft: 40.0 * 200e3,
            f_max: m * 1.08 * 2.0 * MPH,
            cars: 10.0,
            supply: Supply::Ac,
            brake: 2.0 * MPH,
            aux: 300e3,
            i_max: f64::INFINITY,
            v0: 750.0,
            sharing: 1.0,
        }
    }

    /// On a long run with a low limit, the train spends nearly all its time at the limit.
    #[test]
    fn cruises_at_the_limit() {
        let n = 20_001;
        let t = run(&m8(), &vec![30.0; n], &vec![0.0; n], 5.0);
        let at_limit = 100_000.0 / (30.0 * MPH);
        assert!(t > at_limit && t < at_limit + 30.0, "{t} vs {at_limit}");
    }

    /// Third rail with no resistance gives rated power, so it matches 25 kV.
    #[test]
    fn zero_resistance_third_rail_matches_ac() {
        let ac = m8();
        let rail = Train {
            supply: Supply::ThirdRail,
            i_max: 1e9,
            ..ac.clone()
        };
        assert!((rail.power(1e-12) - ac.p_shaft).abs() < 1.0);
        let n = 2001;
        let (lim, r) = (vec![80.0; n], vec![1e-9; n]);
        assert!((run(&ac, &lim, &r, 5.0) - run(&rail, &lim, &r, 5.0)).abs() < 1.0);
    }
}
