import numpy as np


class ABTestEngine:

    def __init__(self):

        self.daily_installs = 20_000
        self.simulation_days = 30

        # Sale Configuration
        self.sale_start_day = 15
        self.sale_duration = 10
        self.sale_boost = 0.01

        # New Traffic Source
        self.new_source_start_day = 20
        self.original_source_installs = 12_000
        self.new_source_installs = 8_000

        # Monetization Assumption
        self.avg_iap_value = 1.0  # assumed value per purchase

        # Variant Metrics
        self.variant_metrics = {
            "A": {
                "purchase_ratio": 0.0305,
                "ecpm": 9.80,
                "impressions_per_user": 2.3,
                "retention": {1: 0.53, 3: 0.27, 7: 0.17, 14: 0.06}
            },
            "B": {
                "purchase_ratio": 0.0315,
                "ecpm": 10.80,
                "impressions_per_user": 1.6,
                "retention": {1: 0.48, 3: 0.25, 7: 0.19, 14: 0.09}
            }
        }

    # =====================================================
    # Retention Modeling
    # =====================================================

    def interpolate_retention(self, retention_dict, max_day):

        known_days = sorted(retention_dict.keys())
        curve = {0: 1.0}

        # Interpolate between known checkpoints
        for i in range(len(known_days) - 1):
            d0, d1 = known_days[i], known_days[i + 1]
            r0, r1 = retention_dict[d0], retention_dict[d1]

            k = (np.log(r1) - np.log(r0)) / (d1 - d0)

            for d in range(d0, d1 + 1):
                curve[d] = r0 * np.exp(k * (d - d0))

        # Continue exponential decay beyond last known day
        last_day = known_days[-1]
        prev_day = known_days[-2]

        r_last = retention_dict[last_day]
        r_prev = retention_dict[prev_day]

        k = (np.log(r_last) - np.log(r_prev)) / (last_day - prev_day)

        for d in range(last_day + 1, max_day + 1):
            curve[d] = r_last * np.exp(k * (d - last_day))

        return curve

    def retention_new_source(self, variant, day):
        if variant == "A":
            return 0.58 * np.exp(-0.12 * (day - 1))
        else:
            return 0.52 * np.exp(-0.10 * (day - 1))

    # =====================================================
    # DAU Simulation
    # =====================================================

    def simulate_dau(self, variant, include_new_source=False):

        metrics = self.variant_metrics[variant]
        retention_curve = self.interpolate_retention(
            metrics["retention"], self.simulation_days
        )

        dau_series = []

        for current_day in range(1, self.simulation_days + 1):

            active_users = 0

            for cohort_day in range(1, current_day + 1):

                age = current_day - cohort_day + 1

                if not include_new_source or cohort_day < self.new_source_start_day:

                    installs = self.daily_installs
                    active_users += installs * retention_curve.get(age, 0)

                else:

                    original_users = (
                            self.original_source_installs
                            * retention_curve.get(age, 0)
                    )

                    new_users = (
                            self.new_source_installs
                            * self.retention_new_source(variant, age)
                    )

                    active_users += original_users + new_users

            dau_series.append(active_users)

        return np.array(dau_series)

    # =====================================================
    # Revenue Simulation
    # =====================================================

    # =====================================================
    # Revenue Simulation
    # =====================================================

    def simulate_revenue(self,
                         variant,
                         include_sale=False,
                         include_new_source=False):

        metrics = self.variant_metrics[variant]

        dau = self.simulate_dau(
            variant,
            include_new_source=include_new_source
        )

        purchase_ratio = metrics["purchase_ratio"]
        ecpm = metrics["ecpm"]
        impressions = metrics["impressions_per_user"]

        daily_iap_revenue = []
        daily_ad_revenue = []

        for day in range(1, self.simulation_days + 1):

            pr = purchase_ratio

            # Apply sale boost
            if include_sale:
                if (self.sale_start_day
                        <= day
                        < self.sale_start_day + self.sale_duration):
                    pr += self.sale_boost

            # IAP Revenue
            iap_rev = (
                    dau[day - 1]
                    * pr
                    * self.avg_iap_value
            )

            # Ad Revenue
            ad_rev = (
                    dau[day - 1]
                    * (ecpm / 1000)
                    * impressions
            )

            daily_iap_revenue.append(iap_rev)
            daily_ad_revenue.append(ad_rev)

        daily_iap_revenue = np.array(daily_iap_revenue)
        daily_ad_revenue = np.array(daily_ad_revenue)

        daily_total_revenue = daily_iap_revenue + daily_ad_revenue
        cumulative_total_revenue = np.cumsum(daily_total_revenue)

        return (
            dau,
            daily_total_revenue,
            cumulative_total_revenue,
            daily_iap_revenue,
            daily_ad_revenue
        )
