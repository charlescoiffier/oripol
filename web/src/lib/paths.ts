/** Préfixe de déploiement (sans slash final), '' à la racine. */
export const BASE: string = import.meta.env.BASE_URL.replace(/\/$/, '');
