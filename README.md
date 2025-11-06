# MCP (Model Context Protocol) <br/> Blueprint in Azure – Overview

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2025-11-03

----------

> MCP is about `structured behavior, access control, and responsibilities` from the AI’s perspective, and we expose it (often via HTTP) using whatever hosting option fits best.

> [!TIP]
> You can think of MCP as:
> - **A universal API contract for AI agents.**  
> - **A permissions framework** (AI can only do what’s declared).  
> - **A deployment‑agnostic service** (you choose where/how to host it).

## What MCP Really Is?
> **MCP (Model Context Protocol)** is a **structured contract** between an AI client (like Copilot Studio or Azure AI Foundry) and an external service (your MCP server).

It defines:
  - **What tools exist** (functions the AI can call).  
  - **What inputs they require** (schemas).  
  - **What outputs they return** (structured JSON).  
  - **What resources are available** (read‑only context like docs, schemas, or files).  
  - **What prompts are predefined** (templates the AI can use).  

> [!TIP]
> Like a **set of rules and responsibilities** that tell the AI: `"Here’s what you’re allowed to do, here’s how you call it, and here’s what you’ll get back"`

## Rights & Responsibilities

> From the AI’s perspective:
- **Rights:** It can only call the tools/resources the MCP server advertises.  
- **Responsibilities:** It must respect the input/output schema and handle errors gracefully.  
- **Boundaries:** The AI cannot `“invent”` new tools, it only uses what the MCP server exposes.  

> From developer perspective (as the server owner):
- You decide **what to expose** (e.g., `getCustomerOrders`, `createInvoice`).  
- You enforce **security and governance** (auth, rate limits, logging).  
- You control **where it’s hosted** (local dev, Azure App Service, Container Apps, Functions, etc.).  

## Transport Layer

- MCP itself is **transport‑agnostic**, it can run over **stdio, WebSockets, or HTTP**.  
- In practice, for Copilot Studio and Azure AI Foundry, you’ll usually expose it as an **HTTP(S) endpoint** so it’s accessible in the cloud.  
- That’s why you see multiple hosting options:
  - **Local dev** → run on your laptop, expose via a dev tunnel.  
  - **Azure App Service / Container Apps** → production‑ready, scalable.  
  - **Azure Functions** → serverless, event‑driven.  

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
