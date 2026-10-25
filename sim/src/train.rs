//! A train's resistance, and the power it can draw.

/// Substation output, V (ORM tags the line 750 V).
pub const V0: f64 = 750.0;
/// Train cuts traction below this, V.
pub const V_MIN: f64 = 500.0;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Supply {
    ThirdRail,
    /// Rated power everywhere: a third rail that doesn't sag.
    Stiff,
    Ac,
}

/// A whole consist, in SI units.
#[derive(Clone, Debug)]
pub struct Train {
    /// Mass, kg.
    pub m: f64,
    /// Mass with rotating inertia, kg.
    pub m_eff: f64,
    /// Rated shaft power, W.
    pub p_shaft: f64,
    /// Tractive effort cap, N.
    pub f_max: f64,
    pub cars: f64,
    pub supply: Supply,
    /// Service brake, m/s².
    pub brake: f64,
    /// Auxiliary power, W.
    pub aux: f64,
    /// Line current limit, A.
    pub i_max: f64,
    /// Trains drawing from the same section at once: scales the source resistance.
    pub sharing: f64,
}

impl Train {
    /// Davis resistance, N, at `v` m/s.
    pub fn resist(&self, v: f64) -> f64 {
        let t = self.m / 1000.0;
        21.7 * t + 0.35 * t * v + 3.0 * self.cars * v * v
    }

    /// Shaft power available at a point fed through `r_eff` ohms.
    pub fn power(&self, r_eff: f64) -> f64 {
        if self.supply != Supply::ThirdRail {
            return self.p_shaft;
        }
        let r_eff = r_eff * self.sharing;
        let demand = self.p_shaft / 0.90 + self.aux;
        let disc = V0 * V0 - 4.0 * r_eff * demand;
        let (mut v, mut i) = if disc >= 0.0 {
            let v = (V0 + disc.sqrt()) / 2.0;
            (v, demand / v)
        } else {
            // The network can't deliver the demand: maximum power transfer.
            (V0 / 2.0, V0 / (2.0 * r_eff))
        };
        if i > self.i_max {
            i = self.i_max;
            v = V0 - i * r_eff;
        }
        if v < V_MIN {
            // Shed current until the train voltage is back at the cutoff.
            i = (V0 - V_MIN) / r_eff;
            v = V_MIN;
        }
        (v * i - self.aux).max(0.0) * 0.90
    }
}
