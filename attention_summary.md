
# Attention is All You Need - Summary

This paper introduces the **Transformer**, a novel neural network architecture that relies entirely on **attention mechanisms**. It dispenses with recurrence and convolutions, allowing for significantly more parallelization and achieving state-of-the-art translation quality with less training time.

## Key Concepts

*   **Self-Attention:** The core innovation is the self-attention mechanism, which allows the model to weigh the importance of different parts of the input sequence when processing it. This enables the model to capture long-range dependencies more effectively than recurrent models.
*   **Encoder-Decoder Structure:** The Transformer follows an encoder-decoder structure, where the encoder processes the input sequence and the decoder generates the output sequence. Both the encoder and decoder are composed of multiple layers of self-attention and feed-forward networks.
*   **Multi-Head Attention:** The attention mechanism is applied multiple times in parallel (multi-head attention) to capture different aspects of the input sequence.
*   **Positional Encoding:** Since the Transformer does not have recurrence, positional encodings are added to the input embeddings to provide information about the position of each word in the sequence.

## Advantages

*   **Parallelization:** The Transformer can be trained much faster than recurrent models due to its parallelizable nature.
*   **Long-Range Dependencies:** The self-attention mechanism allows the model to capture long-range dependencies more effectively.
*   **State-of-the-Art Results:** The Transformer has achieved state-of-the-art results on various sequence-to-sequence tasks, including machine translation.

## Architecture

The Transformer architecture consists of:

*   **Encoder:** A stack of N identical layers, each containing a multi-head self-attention mechanism and a position-wise fully connected feed-forward network.
*   **Decoder:** A stack of N identical layers, each containing a multi-head self-attention mechanism, a multi-head attention mechanism over the output of the encoder stack, and a position-wise fully connected feed-forward network.

