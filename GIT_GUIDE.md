# Git and GitHub Beginner Guide

This file is a simple guide for learning how to use Git and GitHub with this project.

It explains:

- what Git is
- what GitHub is
- how to create a GitHub account
- how to create a repository
- how to connect your project to GitHub
- how to push your code
- what was done for this project

## 1. What Is Git?

Git is a version control system.

It helps you:

- track changes in your code
- save versions of your project
- go back to older versions if something breaks
- work safely on projects over time

Think of Git like a save-history system for coding projects.

## 2. What Is GitHub?

GitHub is a website that stores Git repositories online.

It helps you:

- back up your code online
- access your code from different computers
- share your code with others
- collaborate with teammates

Git works on your computer.
GitHub stores your Git project on the internet.

## 3. Create a GitHub Account

If you do not already have a GitHub account:

1. Open [https://github.com](https://github.com)
2. Click `Sign up`
3. Enter your email
4. Create a username
5. Create a password
6. Verify your email address
7. Finish account setup

If you already have a GitHub account, you can skip this part.

## 4. Install Git

If Git is not installed on your computer:

1. Open [https://git-scm.com/downloads](https://git-scm.com/downloads)
2. Download Git for your operating system
3. Install it with the default options

To check if Git is installed, run:

```bash
git --version
```

If Git is installed, it will show a version number.

## 5. Configure Git for the First Time

Git should know your name and email so your commits are properly labeled.

Run these commands once on your computer:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

To check them:

```bash
git config --global user.name
git config --global user.email
```

## 6. Create a Repository on GitHub

To create a new GitHub repository:

1. Log in to GitHub
2. Click the `+` icon in the top-right corner
3. Click `New repository`
4. Enter a repository name
   Example: `adflow-simulator`
5. Optionally add a description
6. Choose `Public` or `Private`
7. Click `Create repository`

After that, GitHub gives you a repository URL, for example:

```text
https://github.com/your-username/adflow-simulator.git
```

That URL is what connects your local project to GitHub.

## 7. Start Git in a Local Project

Open a terminal inside your project folder and run:

```bash
git init -b main
```

This creates a local Git repository.

## 8. Add a `.gitignore` File

A `.gitignore` file tells Git which files should not be uploaded.

Common examples:

- `.env`
- log files
- virtual environment folders
- Python cache files

Example:

```text
__pycache__/
*.py[cod]
.env
.venv/
venv/
flask-server.log
flask-server.err.log
```

This is important because private credentials should never be pushed to GitHub.

## 9. Connect Local Project to GitHub

After creating your GitHub repo, connect your local folder to it:

```bash
git remote add origin https://github.com/your-username/your-repo.git
```

To verify:

```bash
git remote -v
```

## 10. Save and Push Your Code for the First Time

Use these commands:

```bash
git add .
git commit -m "Initial commit"
git push -u origin main
```

What these commands do:

- `git add .`
  stages all current changes

- `git commit -m "Initial commit"`
  saves your first project snapshot locally

- `git push -u origin main`
  uploads your local `main` branch to GitHub

## 11. What Was Done for This Project

For this project, the following steps were completed:

1. A local Git repository was created in this folder using:

```bash
git init -b main
```

2. A `.gitignore` file was added so these local-only files would not be pushed:

- `.env`
- `flask-server.log`
- `flask-server.err.log`
- `__pycache__/`
- virtual environment folders

3. The GitHub remote repository was connected:

```bash
git remote add origin https://github.com/SantoshMahanty/adflow-simulator.git
```

4. The project files were staged:

```bash
git add .
```

5. The first commit was created:

```bash
git commit -m "Initial commit"
```

6. The code was pushed to GitHub:

```bash
git push -u origin main
```

7. Your project is now available on GitHub here:

[https://github.com/SantoshMahanty/adflow-simulator](https://github.com/SantoshMahanty/adflow-simulator)

## 12. Important Truth About What Was and Was Not Done

I did not create your GitHub account.
I also did not create the GitHub repository itself.

You already gave me this repository URL:

```text
https://github.com/SantoshMahanty/adflow-simulator
```

What I did do was:

- initialize Git in your local project
- add a safe `.gitignore`
- create the first commit
- connect the local project to your existing GitHub repository
- push the code to GitHub

## 13. Daily Git Workflow for Beginners

After making code changes, use this normal workflow:

```bash
git status
git add .
git commit -m "Describe your changes"
git push
```

Example:

```bash
git status
git add .
git commit -m "Updated README and added Git guide"
git push
```

## 14. Useful Beginner Commands

### Check current changes

```bash
git status
```

### See commit history

```bash
git log --oneline
```

### Download latest changes from GitHub

```bash
git pull
```

### Check the connected remote repository

```bash
git remote -v
```

### See which branch you are on

```bash
git branch
```

## 15. Simple Meaning of Common Git Words

- `repository` or `repo`
  A project tracked by Git

- `commit`
  A saved snapshot of your changes

- `branch`
  A separate line of work in Git

- `main`
  The main branch of your project

- `remote`
  The online GitHub repo connected to your local project

- `push`
  Send local commits to GitHub

- `pull`
  Bring changes from GitHub to your computer

- `stage`
  Mark files to be included in the next commit

## 16. Common Mistakes to Avoid

- Do not push `.env` files
- Do not push passwords or API keys
- Do not use very unclear commit messages like `update` or `change`
- Do not forget `git pull` if working on multiple computers

Better commit message examples:

- `Add line item filters`
- `Fix simulator winner logic`
- `Update README for students`
- `Add Git guide`

## 17. If `git push` Fails

Common reasons:

- GitHub login or authentication issue
- wrong repository URL
- no permission to push to the repo
- internet connection issue
- local branch not connected to remote branch

Useful checks:

```bash
git remote -v
git status
git branch
```

Then try:

```bash
git push -u origin main
```

## 18. Recommended Next Step for Learning

Try this once by yourself:

1. Make a very small change in `README.md`
2. Run:

```bash
git status
git add .
git commit -m "Practice commit"
git push
```

3. Refresh your GitHub repository page and confirm the update appears

That is the fastest way to become comfortable with Git.
