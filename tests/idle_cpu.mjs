import { startSim } from "./node_sim.mjs";
const sim = await startSim({ outDir: "/tmp", log: false });
await sim.ready();
const a = process.cpuUsage(); const t = Date.now();
await sim.sleep(5000);
const u = process.cpuUsage(a); const el = Date.now() - t;
console.log("idle CPU over 5s (all threads): " + ((u.user + u.system) / 1000 / el * 100).toFixed(1) + "% of one core");
sim.stop(); process.exit(0);
