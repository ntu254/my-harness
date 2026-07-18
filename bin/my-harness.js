#!/usr/bin/env node
"use strict";

const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const PACKAGE_ROOT = path.resolve(__dirname, "..");
const DEFAULT_REPO = "https://github.com/ntu254/my-harness.git";

function usage() {
  console.log(`my-harness

Run the packaged harness CLI:
  my-harness check
  my-harness --json init

Install a tagged source version into a target directory:
  my-harness install --version v0.2.0 --target ./my-harness-v0.2

Options for install:
  --version <tag-or-branch>   Git ref to install. Default: main
  --target <directory>        Target directory. Default: current directory
  --repo <git-url>            Source repository. Default: ${DEFAULT_REPO}
  --dry-run                   Print the planned action without writing
`);
}

function readPackageVersion() {
  const packagePath = path.join(PACKAGE_ROOT, "package.json");
  return JSON.parse(fs.readFileSync(packagePath, "utf8")).version;
}

function run(cmd, args, options = {}) {
  return childProcess.spawnSync(cmd, args, {
    stdio: options.stdio || "inherit",
    cwd: options.cwd || process.cwd(),
    env: options.env || process.env,
    shell: false
  });
}

function findPython() {
  const candidates = [];
  if (process.env.MY_HARNESS_PYTHON) {
    candidates.push({ cmd: process.env.MY_HARNESS_PYTHON, prefix: [] });
  }
  candidates.push({ cmd: "python3", prefix: [] });
  candidates.push({ cmd: "python", prefix: [] });
  candidates.push({ cmd: "py", prefix: ["-3"] });

  for (const candidate of candidates) {
    const result = run(candidate.cmd, [...candidate.prefix, "--version"], { stdio: "ignore" });
    if (result.status === 0) {
      return candidate;
    }
  }

  console.error("my-harness requires Python 3. Set MY_HARNESS_PYTHON if it is not on PATH.");
  process.exit(127);
}

function runHarness(args) {
  const python = findPython();
  const script = path.join(PACKAGE_ROOT, "cli", "harness.py");
  const env = {
    ...process.env,
    MY_HARNESS_WORKSPACE: process.env.MY_HARNESS_WORKSPACE || process.cwd()
  };
  const result = run(python.cmd, [...python.prefix, script, ...args], { env });
  process.exit(result.status === null ? 1 : result.status);
}

function parseInstallArgs(args) {
  const options = {
    version: "main",
    target: process.cwd(),
    repo: DEFAULT_REPO,
    dryRun: false
  };

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--version") {
      options.version = args[++i];
    } else if (arg === "--target") {
      options.target = args[++i];
    } else if (arg === "--repo") {
      options.repo = args[++i];
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    } else {
      console.error(`unknown install argument: ${arg}`);
      process.exit(2);
    }
  }

  if (!options.version) {
    console.error("missing value for --version");
    process.exit(2);
  }
  if (!options.target) {
    console.error("missing value for --target");
    process.exit(2);
  }
  if (!options.repo) {
    console.error("missing value for --repo");
    process.exit(2);
  }

  options.target = path.resolve(options.target);
  return options;
}

function isEmptyDirectory(dir) {
  if (!fs.existsSync(dir)) {
    return true;
  }
  return fs.statSync(dir).isDirectory() && fs.readdirSync(dir).length === 0;
}

function copyDirContents(source, target) {
  fs.mkdirSync(target, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === "node_modules") {
      continue;
    }
    const from = path.join(source, entry.name);
    const to = path.join(target, entry.name);
    if (entry.isDirectory()) {
      copyDirContents(from, to);
    } else if (entry.isSymbolicLink()) {
      const link = fs.readlinkSync(from);
      fs.symlinkSync(link, to);
    } else {
      fs.copyFileSync(from, to);
    }
  }
}

function installVersion(args) {
  const options = parseInstallArgs(args);
  const action = `clone ${options.repo} at ${options.version} into ${options.target}`;

  if (options.dryRun) {
    console.log(`[dry-run] ${action}`);
    return;
  }

  if (!isEmptyDirectory(options.target)) {
    console.error(`target must be missing or empty: ${options.target}`);
    console.error("Choose a new directory for version testing.");
    process.exit(3);
  }

  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "my-harness-install-"));
  try {
    const clone = run("git", ["clone", options.repo, temp]);
    if (clone.status !== 0) {
      process.exit(clone.status === null ? 1 : clone.status);
    }
    const checkout = run("git", ["checkout", "--quiet", "--detach", options.version], { cwd: temp });
    if (checkout.status !== 0) {
      process.exit(checkout.status === null ? 1 : checkout.status);
    }
    fs.mkdirSync(options.target, { recursive: true });
    copyDirContents(temp, options.target);
    console.log(`installed ${options.version} to ${options.target}`);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

const args = process.argv.slice(2);

if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
  usage();
  process.exit(0);
}

if (args[0] === "--package-version") {
  console.log(readPackageVersion());
  process.exit(0);
}

if (args[0] === "install") {
  installVersion(args.slice(1));
} else {
  runHarness(args);
}
