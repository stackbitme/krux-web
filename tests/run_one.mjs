import { runSequence } from "./seq_runner.mjs";
const [seq, out, locale = "en-US", sd = "sd"] = process.argv.slice(2);
const SEEDS = '{"d668b8b7": {"version": 0, "key_iterations": 100000, "data": "haAyMxFmOVkBE5QixIeJl7P0dYKVeOiuhNodO+qyI2lA+veFUxcXben1OZvKOqTbWNI2Oj8SROTpooiS/4WJdA=="}, "a56dfd6c": {"version": 0, "key_iterations": 100000, "data": "PY9fBDrqtv2ZyZF47CsZ5QucxzXmOxaJJtjkngEQTfHLyLgHTQ3oX8AbZR6+UXBXZUB+eSOHwJZm1jCO8AaBxQ=="}}';
const te = new TextEncoder();
const files = sd ? [
  { path: "sd/settings.json", data: te.encode(JSON.stringify({ settings: { i18n: { locale } } }) + "\n") },
  { path: "sd/seeds.json", data: te.encode(SEEDS + "\n") },
] : [];
const r = await runSequence({ seqFile: seq, outDir: out, files });
if (r.crash) console.log("CRASH", r.crash);
console.log(JSON.stringify({ shots: r.shots.length }));
console.log("slow steps:", JSON.stringify(r.timings.filter(([, t]) => t > 1500 || t < 0)));
process.exit(0);
