import { Connection, clusterApiUrl, PublicKey, Keypair } from "@solana/web3.js";
import { createMint, getOrCreateAssociatedTokenAccount, mintTo } from "@solana/spl-token";
import DLMM from "@meteora-ag/dlmm";
import * as fs from "fs";
import BN from "bn.js";

//devnet pool stuff for testing
const walletData = JSON.parse(fs.readFileSync("./config/devnet_wallet.json", "utf-8"));
const wallet = Keypair.fromSecretKey(new Uint8Array(walletData["secretKey"]));

const connection = new Connection(clusterApiUrl('devnet'), 'confirmed');

async function createPool(): Promise<void> {

    //read pool config
    const poolData = fs.readFileSync("tokens_config.json", "utf-8");
    const tokenXMint = new PublicKey(JSON.parse(poolData)["tokenX"]["mint"]);
    const tokenYMint = new PublicKey(JSON.parse(poolData)["tokenY"]["mint"]);


}

createPool();

// To run tests: ts-node ./src/sdk/test.ts