export const SUBSCRIPTION_ORDER = {
  BRONZE: 10,
  SILVER: 20,
  GOLD: 30,
  PLATINUM: 40,
};

export function hasTier(user, required) {
  if (!user) return false;
  if (user.is_admin) return true;
  if (!user.subscription_active) return false;
  const have = SUBSCRIPTION_ORDER[user.subscription_tier] || 0;
  const need = SUBSCRIPTION_ORDER[required] || 0;
  return have >= need;
}

