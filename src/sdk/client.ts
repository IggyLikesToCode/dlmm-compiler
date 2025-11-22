import {Connection, clusterApiUrl, PublicKey} from "@solana/web3.js";
import DLMM, { BinLiquidity, LbPairAccount } from "@meteora-ag/dlmm"

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

class Client {
    connection: Connection;
    address: PublicKey;

    constructor(connection: Connection, address: PublicKey) {
        this.connection = connection;
        this.address = address;
    }

    async load(poolAddress: string): Promise<DLMM> {
        const pk = new PublicKey(poolAddress);
        const dlmm = await DLMM.create(this.connection, pk);
        return dlmm;
    }

    async getLbPairs(): Promise<LbPairAccount[]> {
        const allPairs = await DLMM.getLbPairs(this.connection);
        return allPairs;
    }

    async getActiveBin(poolAddress: string): Promise<BinLiquidity> {
        const dlmm = await this.load(poolAddress);
        const activeBin = await dlmm.getActiveBin();
        return activeBin;
    }
        
}
