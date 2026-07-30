# Vellum OS — How It Works (Plain English)

---

## Step 1: Upload Your Resume

You upload your resume (PDF). The system reads it using AI and pulls out everything — your name, phone, email, skills, work experience, education, summary, and more. This becomes your "profile" that the system uses for everything else.

Nothing happens to jobs yet. This just sets you up.

---

## Step 2: You Pick a City and Role, Click "Search"

You choose a city (like Bengaluru, Mumbai, NCR) and optionally a role (like "python developer" or "backend engineer"). Then you hit Search.

The system starts working in the background. You see progress updates in real time. You can keep using the UI while it works.

---

## Step 3: The System Goes Through Every Company One by One

This is the big step. The system has a list of 4,000+ companies organized by Indian city. For each company in your chosen city, it tries to find open jobs using two methods:

### Method A: Check if the company uses a known hiring platform

Many companies use platforms like Greenhouse, Lever, Ashby, or Freshteam to post jobs. The system tries to hit these platforms directly using the company's name. If the platform has jobs, it pulls them all — title, description, location, everything. Then it moves to the next company.

### Method B: If no platform found, try the company's career page

If the company doesn't use one of those platforms, the system tries a bunch of common career page URLs — things like careers.company.com, company.com/careers, company.com/jobs. It downloads the page, looks for job listings (either structured data hidden in the page or actual links to job postings), and grabs what it finds.

### What happens to each job it finds

Every job goes through three filters before it makes it to your screen:

1. **Does the role match what you're looking for?** If you searched for "python developer" and the job is for "sales manager", it gets dropped.

2. **Do you have enough experience?** If the job requires 7+ years and you have 3, it gets dropped. If it says "intern" and you're senior, it gets dropped.

3. **Is the job still fresh?** If the posting is older than 30 days or has an expiration date in the past, it gets dropped.

Jobs that survive all three filters get saved to the database.

---

## Step 4: AI Scores Every Job

Once all the companies have been checked and jobs collected, the system sends batches of 10 jobs at a time to an AI model. The AI looks at your profile — your skills, experience, target role, expected salary — and compares it against each job description.

Each job gets a match score from 0 to 1 (like 0.75 or 0.42). The AI also tells you which of your skills match and which skills you're missing.

These scores get saved to the database immediately.

---

## Step 5: You See the Results

Discovery is done. You now see a list of jobs in the Applications tab — company name, job title, match score, location. You can browse through them at your own pace.

Important: at this point, nothing else has happened. No PDFs have been generated. No emails have been sent. No browser has been opened. It's just a clean list of opportunities for you to review.

---

## Step 6: You Click "Apply" on a Job You Like

This is where the per-job pipeline kicks in. You only trigger this for the specific jobs you actually want to apply to. Here's what happens in sequence:

---

### Step 6A: Validate and Build Your Resume

**Freshness check:** The system double-checks that the job is still live by visiting the actual posting page. If it's confirmed dead, it skips.

**Match scoring:** The AI does a deep comparison between your full profile and the job description — checking location fit, experience fit, skills overlap, role alignment, and salary fit. If the match is poor (below 30%), it skips the job.

**Resume tailoring:** If the match is good, the system creates a custom version of your resume for this specific job:

- Your professional summary gets rewritten to highlight the skills and experiences most relevant to this job
- Each bullet point in your work experience gets rewritten using a high-impact format (the Google XYZ formula: "Accomplished X as measured by Y by doing Z")
- The system is careful to only use technologies and skills you actually have — it never invents fake skills

**PDF generation:** A clean, ATS-friendly PDF is created from the tailored content. This is the resume that will be submitted.

---

### Step 6B: Find the Right Person to Contact

The system searches the internet for real people at the company who are involved in hiring — hiring managers, engineering managers, recruiters, founders. It looks across LinkedIn, company websites, and other sources.

Then it tries to find their email address using multiple methods:

1. Check the company's contact or about page for email addresses
2. If it found a person's name, try common email formats (like first@company.com, first.last@company.com)
3. Search Google for email addresses associated with the company
4. Check the company's GitHub repositories for commit author emails
5. As a last resort, try generic addresses like careers@, jobs@, hr@

Each email guess gets checked — the system verifies the email domain has proper mail servers, and for the top candidates, it even tests whether the email address actually exists without sending anything.

---

### Step 6C: Draft a Cold Email

Using the contact person found and the tailored resume, the AI writes a short, professional cold email. It's under 150 words, references the specific role and company, highlights one or two of your most relevant skills, and ends with a clear ask.

The email gets saved as a draft with a mailto link and a Gmail compose link, so you can send it with one click.

---

### Step 6D: Auto-Fill the Application Form

The system opens a real browser (like a normal person would use), goes to the job application page, and starts filling in the form fields using your profile information — name, email, phone, resume upload, and any other standard fields.

If it hits a wall — like a login screen, a CAPTCHA, or a multi-factor authentication prompt — it pauses and asks you to handle that part manually. You can take over the browser window, do what's needed, and then tell the system to continue.

The system takes screenshots at every step so you can see what's happening.

---

## Step 7: Done

The full cycle for that one job is complete. Your tailored resume has been generated, a cold email draft is ready to send, and the application form has been submitted (or is waiting for your manual input on a tricky step).

You can then go back to the list and click Apply on another job, and the whole Step 6 process runs again for that new job — independently, with its own tailored resume and everything.

---

## The Two Modes at a Glance

| What you do | What the system does |
|---|---|
| Click "Search" | Goes through thousands of companies, finds jobs, scores them, shows you the list |
| Click "Apply" on one job | Builds a custom resume for that job, finds the hiring person, drafts an email, fills the application |

The search never builds resumes or sends emails. The apply only runs for the one job you picked.

---

## Key Files and What They Do

| File | What it handles |
|---|---|
| routes.py | All the HTTP endpoints — upload resume, start search, apply, etc. |
| graph.py | The brain — connects all the steps together, decides what runs when |
| career_scraper.py | The company-by-company scraper — hits ATS platforms and career pages |
| career_urls.py | The database of URL patterns and which companies use which hiring platform |
| ats_api.py | The connectors for Greenhouse, Lever, Ashby, Freshteam, and others |
| geo_search.py | The top-level discovery — calls career_scraper, then checks VC portfolio boards |
| job_evaluator.py | The filter — heuristic scoring plus AI batch evaluation |
| validator_tailor.py | The resume builder — validates the match, tailoring summary and bullets, generates PDF |
| contact_finder.py | The people finder — searches for hiring contacts and their emails |
| email_drafter.py | The email writer — creates cold outreach drafts |
| browser_agent.py | The form filler — opens a real browser, fills application forms, handles blockers |
| email_handoff.py | The email tool — generates email permutations, verifies addresses, creates mailto links |
| scrape.py | The page fetcher — downloads web pages using browser-like headers |
| database.py | The storage — SQLite database for profiles, jobs, drafts |
| llm_router.py | The AI router — picks the right AI model for each task |
| models.py | The data structures — defines what a profile, job, or email draft looks like |
