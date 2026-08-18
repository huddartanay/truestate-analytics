# Streamlit Community Cloud Deployment Guide

This guide provides step-by-step instructions on how to host the **Abu Dhabi Real Estate Market Intelligence Dashboard** permanently on Streamlit Community Cloud for free.

---

## 📋 Prerequisites
1. A [GitHub Account](https://github.com/join).
2. [Git installed](https://git-scm.com/downloads) on your computer.
3. A [Streamlit Community Cloud Account](http://share.streamlit.io/) (you can log in directly using your GitHub credentials).

---

## 🛠️ Step-by-Step Hosting Instructions

### Step 1: Create a GitHub Repository
1. Log in to [GitHub](https://github.com/).
2. In the top-right corner, click the **`+`** icon and select **New repository**.
3. Name your repository (e.g., `abu-dhabi-real-estate-dashboard`).
4. Set the visibility to **Public** (required for the free tier of Streamlit Cloud).
5. Leave "Add a README file", "Add .gitignore", and "Choose a license" **unchecked** (we already have these in the codebase).
6. Click **Create repository**.

### Step 2: Push the Code to GitHub
Open your Terminal (macOS/Linux) or Command Prompt (Windows) and run the following commands to push the project to your new repository:

```bash
# 1. Navigate to the project directory
cd "/Users/tanayhuddar/Desktop/abu dhabi dashboard"

# 2. Add the remote GitHub repository URL (replace with your own repository URL)
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/abu-dhabi-real-estate-dashboard.git

# 3. Rename the branch to main (if not already main)
git branch -M main

# 4. Push the code to GitHub
git push -u origin main
```

---

### Step 3: Connect and Deploy on Streamlit Community Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/) and click **Sign in with GitHub**.
2. Once logged in, click the **New app** button (top right).
3. Fill in the deployment details:
   - **Repository**: Choose `YOUR_GITHUB_USERNAME/abu-dhabi-real-estate-dashboard`.
   - **Branch**: Set to `main`.
   - **Main file path**: Set to **`app.py`** (this is the entry point of the app).
4. Click **Deploy!**

Your application will build and deploy (typically takes 1–2 minutes). Streamlit will assign a permanent public URL (e.g., `https://your-app-name.streamlit.app/`) which remains online 24/7.

---

## 🔄 How to Update the Deployment in the Future
Streamlit Community Cloud is connected directly to your GitHub repository. Any changes pushed to GitHub are **automatically** built and deployed to the live website instantly.

When you modify your code locally and want to deploy the update:
```bash
# 1. Stage the changed files
git add .

# 2. Commit the changes
git commit -m "Update visualizations and styling"

# 3. Push to GitHub (the live site will update automatically)
git push origin main
```
