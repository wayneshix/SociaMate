# SociaMate API Documentation

## Overview

SociaMate API provides endpoints for managing conversations, retrieving context, and generating summaries of chat histories. The API is built with FastAPI and provides features for handling large conversations efficiently.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication for development purposes. In a production environment, proper authentication would be implemented.

## Endpoints

### Legacy Summarization Endpoint

#### POST /summarize

Summarizes text directly without storing it.

**Request Body:**
```json
{
  "text": "string"
}
```

**Response:**
```json
{
  "summary": "string",
  "processing_time": 0.0
}
```

### Conversation Management

#### POST /conversations

Create a new conversation from a list of messages.

**Request Body:**
```json
{
  "messages": [
    {
      "author": "string",
      "content": "string",
      "timestamp": "2023-10-17T12:00:00Z",
      "metadata": {}
    }
  ],
  "conversation_id": "string"  // Optional, will be generated if not provided
}
```

**Response:**
```json
{
  "conversation_id": "string",
  "message_count": 0,
  "processing_time": 0.0
}
```

#### POST /conversations/{conversation_id}/messages

Add a message to an existing conversation.

**Path Parameters:**
- `conversation_id` - ID of the conversation

**Request Body:**
```json
{
  "author": "string",
  "content": "string",
  "timestamp": "2023-10-17T12:00:00Z",
  "metadata": {}
}
```

**Response:**
```json
{
  "message_id": 0,
  "conversation_id": "string",
  "processing_time": 0.0
}
```

#### GET /conversations/{conversation_id}/messages

Get messages from a conversation.

**Path Parameters:**
- `conversation_id` - ID of the conversation

**Query Parameters:**
- `skip` - Number of messages to skip (default: 0)
- `limit` - Maximum number of messages to return (default: 100, max: 1000)

**Response:**
```json
{
  "conversation_id": "string",
  "messages": [
    {
      "id": 0,
      "conversation_id": "string",
      "author": "string",
      "content": "string",
      "timestamp": "2023-10-17T12:00:00Z",
      "metadata": {}
    }
  ],
  "count": 0,
  "processing_time": 0.0
}
```

### Context and Summarization

#### GET /conversations/{conversation_id}/context

Get the relevant context for a conversation.

**Path Parameters:**
- `conversation_id` - ID of the conversation

**Query Parameters:**
- `query` - Optional query to filter context by relevance

**Response:**
```json
{
  "context": "string",
  "context_size": 0,
  "processing_time": 0.0
}
```

#### GET /conversations/{conversation_id}/summary

Get a summary for a conversation.

**Path Parameters:**
- `conversation_id` - ID of the conversation

**Query Parameters:**
- `query` - Optional query to focus the summary on
- `force_refresh` - Whether to force a refresh of the summary (default: false)

**Response:**
```json
{
  "summary": "string",
  "processing_time": 0.0
}
```

## Error Responses

The API returns standard HTTP status codes:

- `200 OK` - The request was successful
- `201 Created` - A new resource was created
- `400 Bad Request` - The request was invalid
- `404 Not Found` - The requested resource was not found
- `500 Internal Server Error` - An error occurred on the server

Error responses include a JSON body with details:

```json
{
  "detail": "Error message"
}
```

## Configuration

The API can be configured through environment variables:

- `DATABASE_URL` - PostgreSQL connection URL
- `REDIS_HOST` - Redis host
- `REDIS_PORT` - Redis port
- `REDIS_PASSWORD` - Redis password
- `HF_TOKEN` - Hugging Face API token

## Metrics

The API collects metrics on:
- Database query time
- Embedding generation latency
- Cache hit rate
- Context retrieval time

These metrics can be used to monitor performance and identify bottlenecks. 