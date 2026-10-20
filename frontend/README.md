# Front Pay-Now

Interface de paiement (React, TypeScript, Tailwind, Vite) branchée sur la passerelle du projet.

## Développement

```bash
cd frontend
npm ci
npm run dev      # http://localhost:5173
```

Les appels `/auth` et `/me` sont relayés par Vite vers le WAF publié en local (`http://127.0.0.1:8080`) :
la pile Docker Compose doit tourner. Les données sont fictives.

## Déploiement

Le front est construit dans l'image `gateway` (`infra/compose/gateway/Dockerfile`) et servi par Caddy derrière le WAF :
`docker compose -f infra/compose/docker-compose.yml up -d --build`, puis `http://127.0.0.1:8080`.

## Session

Jeton et profil restent en `sessionStorage` : un rafraîchissement ne déconnecte pas. Au chargement, le solde est relu
via `GET /me/account` ; un 401 (jeton expiré) déconnecte. Voir `src/session.ts`.

## Contrôles

```bash
npm run lint     # erreurs bloquantes, `any` signalés en avertissement
npm run build    # vérification des types + build de production
```

## Choix

- Aucun script tiers : pas de SDK de paiement externe ni de CDN, tout est servi par le projet.
- Peu de dépendances, par contrainte de RAM : React, Recoil, Axios, Framer Motion, Flowbite (styles).
- Les écrans sans équivalent dans le back (ajout d'argent, prêt, PIN…) ne sont pas repris.
