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
  const tierCode = (user.subscription_tier || "").toUpperCase();
  const have = SUBSCRIPTION_ORDER[tierCode] || 0;
  const need = SUBSCRIPTION_ORDER[required] || 0;
  return have >= need;
}

export function getUserHomePath(user) {
  if (hasTier(user, "GOLD")) return "/user/winner-products";
  if (hasTier(user, "SILVER")) return "/user/analytics";
  if (hasTier(user, "BRONZE")) return "/user/reporter-setup";
  return "/user/subscriptions";
}

