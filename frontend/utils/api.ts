import Papa from "papaparse";
import { v4 as uuidv4 } from "uuid";

// Cache for conversation IDs
const conversationCache: { [key: string]: string } = {};

// Helper to parse CSV message data
function parseCSVMessages(text: string) {
  try {
    const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
    if (!parsed.data || parsed.data.length === 0) {
      return null;
    }
    
    // Convert CSV data to message format
    return parsed.data.map((row: any) => ({
      author: row.user_name || row.author || row.sender || "Unknown",
      content: row.content || row.message || row.text || "",
      // If timestamp exists, use it; otherwise, leave it undefined
      timestamp: row.timestamp ? new Date(row.timestamp).toISOString() : undefined,
    }));
  } catch (error) {
    console.error("Failed to parse CSV", error);
    return null;
  }
}

// Function to use the new endpoints
async function sendToNewAPI(text: string) {
  try {
    // Generate a hash or use cached conversation ID
    const textHash = btoa(text.substring(0, 100)).replace(/[^a-zA-Z0-9]/g, "");
    let conversationId = conversationCache[textHash];
    
    // Parse messages if it's CSV data
    const messages = parseCSVMessages(text);
    
    if (!messages) {
      // If not CSV or parsing failed, use the legacy endpoint
      return sendToLegacyAPI(text);
    }
    
    if (!conversationId) {
      // Create new conversation
      const createResponse = await fetch("http://localhost:8000/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages, conversation_id: uuidv4() }),
      });
      
      if (!createResponse.ok) {
        throw new Error("Failed to create conversation");
      }
      
      const result = await createResponse.json();
      conversationId = result.conversation_id;
      
      // Cache the conversation ID
      conversationCache[textHash] = conversationId;
    }
    
    // Get summary using the new endpoint
    const summaryResponse = await fetch(`http://localhost:8000/conversations/${conversationId}/summary`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    
    if (!summaryResponse.ok) {
      throw new Error("Failed to get summary");
    }
    
    return await summaryResponse.json();
  } catch (error) {
    console.error("Error with new API, falling back to legacy", error);
    // Fall back to legacy API if anything fails
    return sendToLegacyAPI(text);
  }
}

// Legacy API function
async function sendToLegacyAPI(text: string) {
  const response = await fetch("http://localhost:8000/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    throw new Error("Failed to summarize");
  }

  return await response.json();
}

// Main export function that tries new API first, then falls back
export async function sendTextToBackend(text: string) {
  try {
    // Try to use the new API with conversation endpoints
    return await sendToNewAPI(text);
  } catch (error) {
    console.error("Error with new API flow:", error);
    // Fall back to legacy API
    return await sendToLegacyAPI(text);
  }
}

// Draft response API function
export async function sendTextForDraftResponse(text: string, asUser?: string) {
  const response = await fetch("http://localhost:8000/draft_response", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      text,
      as_user: asUser 
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to draft response");
  }

  return await response.json();
}