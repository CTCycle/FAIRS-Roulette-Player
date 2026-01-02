const fs = require('fs');
const path = require('path');

const source = String.raw`C:\Users\Thomas V\.gemini\antigravity\brain\7fa5e3bd-4e4d-408d-bd73-96df26114f2c\roulette_wheel_icon_1767350605605.png`;
const dest = 'roulette_wheel.png';
const logFile = 'node_copy_log.txt';

try {
    fs.writeFileSync(logFile, `Starting copy from ${source}\n`);
    if (!fs.existsSync(source)) {
        fs.appendFileSync(logFile, `Error: Source not found at ${source}\n`);
    } else {
        fs.copyFileSync(source, dest);
        fs.appendFileSync(logFile, "Success: File copied.\n");
        if (fs.existsSync(dest)) {
            fs.appendFileSync(logFile, `Verified: ${dest} exists.\n`);
        } else {
            fs.appendFileSync(logFile, `Error: ${dest} not found after copy.\n`);
        }
    }
} catch (e) {
    try {
        fs.appendFileSync(logFile, `Exception: ${e.message}\n`);
    } catch (err) {
        // ignore
    }
}
