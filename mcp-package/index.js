#!/usr/bin/env node

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} = require('@modelcontextprotocol/sdk/types.js');
const axios = require('axios');

// Configuration from environment variables
const DJINSIGHT_URL = process.env.DJINSIGHT_URL || 'http://localhost:8000';
const DJINSIGHT_API_KEY = process.env.DJINSIGHT_API_KEY || '';

// Create axios instance
const api = axios.create({
  baseURL: `${DJINSIGHT_URL}/djinsight/mcp/`,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${DJINSIGHT_API_KEY}`
  },
  timeout: 30000
});

// Create MCP server
const server = new Server(
  {
    name: 'djinsight-mcp',
    version: '0.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  try {
    console.error('Fetching tools from Django...');
    const response = await api.post('', { action: 'list_tools' });
    console.error('Tools fetched successfully:', response.data.tools.length);
    return {
      tools: response.data.tools
    };
  } catch (error) {
    console.error('Error listing tools:', error.message);
    if (error.response) {
        console.error('Response data:', error.response.data);
        console.error('Response status:', error.response.status);
    }
    return { tools: [] };
  }
});

// Call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;
    
    const response = await api.post('', {
      action: 'execute_tool',
      tool_name: name,
      arguments: args
    });
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2)
        }
      ]
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`
        }
      ],
      isError: true
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('djinsight-mcp server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
