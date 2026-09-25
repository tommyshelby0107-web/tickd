# Deploying tickd (free, every feature working)

**Where:** Render's free plan, as a Docker container. The container includes Tesseract, so scanned PDFs are read,
and it runs as one long-lived process, so the queue, bulk runs, the live view and the email inbox all work.
It needs no credit card.

**Why not Vercel:** Vercel runs code only while it answers a request and its disk is temporary. Tesseract can't be
installed, the background queue would stop after each request, and the database would be wiped.

**The one catch:** a free Render service sleeps after 15 minutes without visits, and waking wipes its disk (runs,
and any vendors or POs added in the app). A free uptime monitor that visits every 5 minutes keeps it awake 24/7.
750 free hours a month covers one service running all month.

## 1. Put the code on GitHub (private)

1. Create a new **private** repository at https://github.com/new, for example `tickd`. Leave it empty
   (no README).
2. In this folder:

   ```powershell
   git remote add origin https://github.com/<your-username>/tickd.git
   git push -u origin main
   ```

   `.env` (your keys) and `storage/` (your local data) are in `.gitignore`, so they are never uploaded.

## 2. Create the service on Render

1. Sign up at https://render.com with your GitHub account (free, no card).
2. **New → Blueprint**, pick the `tickd` repository. Render reads `render.yaml`.
3. It asks for the secret values. Copy them from your local `.env`:
   `GROQ_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`, and for email `EMAIL_ADDRESS`, `EMAIL_APP_PASSWORD`,
   `EMAIL_TRUSTED_FORWARDERS`.
4. **Apply.** The first build takes about 3–5 minutes. The app is then at `https://tickd-xxxx.onrender.com`.
5. Check `https://tickd-xxxx.onrender.com/api/health` shows `{"ok":true,...}`.

Every later `git push` to `main` redeploys automatically (the demo data then starts fresh).

## 3. Keep it awake

1. Sign up at https://uptimerobot.com (free).
2. **New monitor → HTTP(s)**, URL `https://tickd-xxxx.onrender.com/api/health`, interval **5 minutes**.

## 4. Before sharing the link

- **Email:** only one copy of the app should read the Gmail inbox. Once the hosted app has the `EMAIL_*`
  settings, remove them from your local `.env` (or keep the local app off). Otherwise both copies race for
  the same emails.
- **Warm it up:** open the link a couple of minutes before a demo, in case it has just restarted.
- **Mistral:** its free plan still needs switching on at console.mistral.ai (Admin → Subscriptions →
  Experiment). Until then photos and poor scans are read by Gemini only.
- **After the case study:** regenerate the Gemini, Groq and Mistral keys and the Gmail app password.

## Running the same container anywhere else

The `Dockerfile` works on any Docker host (Railway, Google Cloud, a VM). The host sets `PORT`; secrets are
environment variables with the same names as in `.env.example`.
