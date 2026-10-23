# CivicSathi AI — judge pitch

## 90-second pitch

> Good morning. We are building CivicSathi AI, a citizen-friendly digital front door for Chandigarh civic services.
>
> People often know what problem they have, but not which department handles it, which service form to choose, or how to follow up. That friction is especially hard for seniors and people who are less comfortable navigating government portals.
>
> CivicSathi lets a resident explain a need in their own words, by typing or speaking, and can use a photo as supporting context. Google Gemma helps identify the likely service and organize the details into a clear draft. The resident reviews and corrects that draft before submitting it. They can then track the request in one account, hear responses aloud, or find nearby Sampark centre help.
>
> We have focused our demo on practical Chandigarh use cases: civic complaints, horticulture, GMSH-16 appointment requests, and senior-citizen, disability and pension assistance. The app uses individual accounts and a persistent database in deployment, while keeping a lightweight SQLite option for local development.
>
> CivicSathi is designed as an assistive layer around existing public services. It does not claim to book a real hospital appointment or submit an application to a government system. Our next step is to evaluate routing and image accuracy with consented, representative examples, then integrate only through authorized APIs.
>
> Our goal is simple: make the first step into a civic service clearer, more accessible and easier to track. Thank you.

## Live demo sequence (about 2 minutes)

1. Start on the landing page and explain that this is a prototype, not an official Chandigarh portal.
2. Sign in with a prepared judge/demo account. Avoid registering live during the pitch.
3. Open **Ask CivicSathi** and say or type: “My elderly mother needs help applying for a senior citizen card, and we would like to know where to get assistance.”
4. Show the suggested service/category and extracted details. Emphasize the citizen review step; edit one field if useful.
5. Submit and show the tracking ID, then open **Track** to show request status/history.
6. Show the **Nearby help** option for Sampark centre navigation. Explain that the browser opens map results and the app does not store precise location.
7. If time allows, show the photo analysis flow and its confirmation step. Do not imply one successful sample proves accuracy.

Have a backup screenshot or pre-created request ready in case Wi-Fi or the model API is slow. Never show API keys, passwords, personal records, or an actual resident's image.

## Likely judge questions

**What does AI add?** It converts an open-ended request into a proposed category, service and structured draft, and can interpret a supporting image. It reduces form-selection friction; the citizen remains in control and must confirm before saving.

**How do you protect citizens from a wrong AI answer?** The result is presented as a suggestion, not an official decision. People review and edit it, and the prototype does not approve benefits, make enforcement decisions or claim government-system access. We need representative evaluation and human review before any consequential deployment.

**Is it connected to Chandigarh systems?** No. It stores demo requests in its own database and tracks their demo status. Hospital bookings, benefit applications and government submissions are not real transactions. Integration would require authorization and official APIs.

**How do you measure success?** Evaluate service-routing accuracy, category precision/recall, image classification on a labeled set, multilingual task completion, and usability with older residents. We have not yet established production accuracy or measured impact, so present these as evaluation goals rather than results.

**How will it scale and keep data?** The code supports SQLite locally and PostgreSQL in hosted deployment. A public deployment must use a persistent managed database, secure environment variables, HTTPS, backups, and data minimization. The current demo should use synthetic/test data only.

**Why Chandigarh?** The experience is grounded in Chandigarh's published e-Sampark services and common citizen journeys, with Sampark centre assistance as a physical support path. We are extending access to services rather than suggesting those services do not already exist.
