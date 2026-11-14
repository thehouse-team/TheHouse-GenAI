"""LLM provider abstractions.

Spec 002 introduces the vendor-neutral LLM port: the `GenerativeAiProvider` protocol,
its immutable DTOs, the provider error taxonomy, the central guard that enforces the
input limit and the timeout, a deterministic `FakeProvider` test double and the
selection factory. Everything in this package is offline: no module opens a socket and
no real provider is registered. The concrete adapter for a real provider arrives with
spec 011, behind the same port.
"""
