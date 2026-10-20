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

## Contrôles

```bash
npm run lint     # erreurs bloquantes, `any` signalés en avertissement
npm run build    # vérification des types + build de production
```

## Choix

- Aucun script tiers : pas de SDK de paiement externe ni de CDN, tout est servi par le projet.
- Peu de dépendances, par contrainte de RAM : React, Recoil, Axios, Framer Motion, Flowbite (styles).
- Les écrans sans équivalent dans le back (ajout d'argent, prêt, PIN…) ne sont pas repris.
