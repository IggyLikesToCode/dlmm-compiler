import { Connection, PublicKey, Keypair } from "@solana/web3.js";
import { StrategyType } from "@meteora-ag/dlmm";
import BN from "bn.js";
import * as fs from "fs";
import Client from "./client";

/**
 * Strategy plan interface - matches Python export format
 */
export interface StrategyPlan {
    version: string;
    generated_at: string;
    metrics: {
        r_squared: number;
        residual: number;
        truncated: boolean;
        full_r_squared: number;
    };
    strategies: Array<{
        type: "rectangle" | "curve" | "bid_ask";
        center: number;
        width: number;
        weight: number;
    }>;
    pool_config?: {
        poolAddress: string;
        binStep: number;
        activeBin: number;
    };
}

/**
 * Map Python strategy types to Meteora StrategyType
 */
function mapStrategyType(pythonType: string): StrategyType {
    switch (pythonType) {
        case "rectangle":
            return StrategyType.Spot;
        case "curve":
            return StrategyType.Curve;
        case "bid_ask":
            return StrategyType.BidAsk;
        default:
            throw new Error(`Unknown strategy type: ${pythonType}`);
    }
}

/**
 * Load a strategy plan from JSON file
 */
export function loadStrategyPlan(filePath: string): StrategyPlan {
    const content = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(content) as StrategyPlan;
}

/**
 * Calculate bin range for a strategy based on center and width
 */
function calculateBinRange(
    center: number,
    width: number,
    activeBin: number
): { minBinId: number; maxBinId: number } {
    // Convert relative center to absolute bin ID
    // center is relative to the active bin
    const absoluteCenter = activeBin + center;
    const halfWidth = Math.floor(width / 2);
    
    return {
        minBinId: absoluteCenter - halfWidth,
        maxBinId: absoluteCenter + halfWidth
    };
}

/**
 * Execute a strategy plan by creating positions on Meteora
 * 
 * @param client - Meteora client instance
 * @param plan - Strategy plan from Python optimizer
 * @param poolAddress - Pool address to deploy to
 * @param totalXAmount - Total X token amount to deploy
 * @param totalYAmount - Total Y token amount to deploy
 * @param activeBin - Current active bin ID
 * @param slippage - Optional slippage tolerance (default 1%)
 * @returns Array of position public keys created
 */
export async function executeStrategyPlan(
    client: Client,
    plan: StrategyPlan,
    poolAddress: string,
    totalXAmount: BN,
    totalYAmount: BN,
    activeBin: number,
    slippage: number = 1
): Promise<string[]> {
    console.log("\n" + "=".repeat(60));
    console.log("EXECUTING STRATEGY PLAN");
    console.log("=".repeat(60));
    console.log(`Plan version: ${plan.version}`);
    console.log(`Generated at: ${plan.generated_at}`);
    console.log(`R² quality: ${plan.metrics.r_squared.toFixed(4)}`);
    console.log(`Strategies to deploy: ${plan.strategies.length}`);
    console.log(`Pool: ${poolAddress}`);
    console.log(`Active bin: ${activeBin}`);
    
    const positionKeys: string[] = [];
    
    for (let i = 0; i < plan.strategies.length; i++) {
        const strat = plan.strategies[i];
        console.log(`\n--- Strategy ${i + 1}/${plan.strategies.length} ---`);
        console.log(`  Type: ${strat.type} -> ${mapStrategyType(strat.type)}`);
        console.log(`  Center: ${strat.center}, Width: ${strat.width}`);
        console.log(`  Weight: ${(strat.weight * 100).toFixed(2)}%`);
        
        // Calculate token amounts based on weight
        const xAmount = new BN(totalXAmount.muln(Math.floor(strat.weight * 10000)).divn(10000));
        const yAmount = new BN(totalYAmount.muln(Math.floor(strat.weight * 10000)).divn(10000));
        
        console.log(`  X Amount: ${xAmount.toString()}`);
        console.log(`  Y Amount: ${yAmount.toString()}`);
        
        // Calculate bin range
        const { minBinId, maxBinId } = calculateBinRange(strat.center, strat.width, activeBin);
        console.log(`  Bin range: ${minBinId} to ${maxBinId}`);
        
        // Create strategy parameters
        const strategyParams = await client.createStrategy(
            mapStrategyType(strat.type),
            minBinId,
            maxBinId
        );
        
        // Create position
        try {
            await client.createPosition(
                poolAddress,
                xAmount,
                yAmount,
                strategyParams,
                slippage
            );
            console.log(`  ✓ Position created successfully`);
            // Note: The actual position key would need to be captured from createPosition
            // For now we log success
        } catch (error) {
            console.error(`  ✗ Failed to create position: ${error}`);
            throw error;
        }
    }
    
    console.log("\n" + "=".repeat(60));
    console.log(`EXECUTION COMPLETE: ${plan.strategies.length} positions created`);
    console.log("=".repeat(60));
    
    return positionKeys;
}

/**
 * Preview what would be executed without actually deploying
 */
export function previewStrategyPlan(
    plan: StrategyPlan,
    totalXAmount: BN,
    totalYAmount: BN,
    activeBin: number
): void {
    console.log("\n" + "=".repeat(60));
    console.log("STRATEGY PLAN PREVIEW (DRY RUN)");
    console.log("=".repeat(60));
    console.log(`Plan version: ${plan.version}`);
    console.log(`Generated at: ${plan.generated_at}`);
    console.log(`\nMetrics:`);
    console.log(`  R² quality: ${plan.metrics.r_squared.toFixed(4)}`);
    console.log(`  Residual: ${plan.metrics.residual.toFixed(6)}`);
    console.log(`  Truncated: ${plan.metrics.truncated}`);
    
    console.log(`\nDeployment:`);
    console.log(`  Active bin: ${activeBin}`);
    console.log(`  Total X: ${totalXAmount.toString()}`);
    console.log(`  Total Y: ${totalYAmount.toString()}`);
    
    console.log(`\nStrategies (${plan.strategies.length}):`);
    
    for (let i = 0; i < plan.strategies.length; i++) {
        const strat = plan.strategies[i];
        const { minBinId, maxBinId } = calculateBinRange(strat.center, strat.width, activeBin);
        const xAmount = new BN(totalXAmount.muln(Math.floor(strat.weight * 10000)).divn(10000));
        const yAmount = new BN(totalYAmount.muln(Math.floor(strat.weight * 10000)).divn(10000));
        
        console.log(`\n  ${i + 1}. ${strat.type.toUpperCase()}`);
        console.log(`     Meteora type: ${mapStrategyType(strat.type)}`);
        console.log(`     Center: ${strat.center}, Width: ${strat.width}`);
        console.log(`     Bin range: ${minBinId} to ${maxBinId}`);
        console.log(`     Weight: ${(strat.weight * 100).toFixed(2)}%`);
        console.log(`     X allocation: ${xAmount.toString()}`);
        console.log(`     Y allocation: ${yAmount.toString()}`);
    }
    
    console.log("\n" + "=".repeat(60));
}

// CLI usage example
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 1) {
        console.log("Usage: ts-node executor.ts <strategy_plan.json> [--preview]");
        console.log("\nOptions:");
        console.log("  --preview    Preview the plan without executing");
        process.exit(1);
    }
    
    const planPath = args[0];
    const isPreview = args.includes("--preview");
    
    console.log(`Loading strategy plan from: ${planPath}`);
    const plan = loadStrategyPlan(planPath);
    
    // Example values - in real usage these would come from config
    const totalX = new BN("1000000000"); // 1 token with 9 decimals
    const totalY = new BN("1000000");    // 1 token with 6 decimals
    const activeBin = 0; // Would come from pool query
    
    if (isPreview) {
        previewStrategyPlan(plan, totalX, totalY, activeBin);
    } else {
        console.log("\nTo execute, connect wallet and call executeStrategyPlan()");
        console.log("Running preview instead...");
        previewStrategyPlan(plan, totalX, totalY, activeBin);
    }
}

// Run if called directly
main().catch(console.error);
