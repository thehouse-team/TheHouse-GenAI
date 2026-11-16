"""LLM provider abstractions.

Spec 002 introduces the vendor-neutral LLM port: the `GenerativeAiProvider` protocol,
its immutable DTOs, the provider error taxonomy, the central guard that enforces the
input limit and the timeout, a deterministic `FakeProvider` test double and the
selection factory. Spec 011 adds `GeminiProvider`, the concrete adapter behind the
same port: it is the only module of the service that speaks HTTP, and the test suite
never reaches the network.
"""
