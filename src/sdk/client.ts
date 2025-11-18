import {Connection, clusterApiUrl} from "@solana/web3.js";

async function checkConnection(): Promise<void> {
    const connection = new Connection(clusterApiUrl('devnet'), 'confirmed');

    const version = await connection.getVersion();
    console.log("Solana Cluster version:", version);

    const slot = await connection.getSlot();
    console.log("Current slot:", slot);
}

checkConnection().catch(err => {
    console.error("Error connecting to Solana cluster:", err);
});

// To check connection run `ts-node ./src/sdk/client.ts`