// Cross-platform "pip install -r requirements.txt" into ./.venv.
// Needed because Windows and POSIX venvs put the pip executable in
// different subfolders (Scripts/pip.exe vs bin/pip).
const { execFileSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const isWin = process.platform === "win32";
const pip = path.join(
  __dirname,
  "..",
  ".venv",
  isWin ? "Scripts" : "bin",
  isWin ? "pip.exe" : "pip"
);

if (!fs.existsSync(pip)) {
  console.error(
    `Could not find ${pip}. Run "npm run setup --workspace=backend" from the repo root, ` +
      `which creates .venv before this script runs.`
  );
  process.exit(1);
}

execFileSync(pip, ["install", "-r", "requirements.txt"], {
  cwd: path.join(__dirname, ".."),
  stdio: "inherit",
});