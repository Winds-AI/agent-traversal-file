package main

import (
	"github.com/tliron/commonlog"
	_ "github.com/tliron/commonlog/simple"
	"github.com/tliron/glsp"
	protocol "github.com/tliron/glsp/protocol_3_16"
	"github.com/tliron/glsp/server"

	"github.com/Winds-AI/agent-traversal-file/lsp/analyzer"
)

const lsName = "IATF Language Server"

var version string = "0.1.0"
var handler protocol.Handler
var documentStore = analyzer.NewDocumentStore()

func main() {
	commonlog.Configure(1, nil)

	handler = protocol.Handler{
		Initialize:                 initialize,
		Initialized:                initialized,
		Shutdown:                   shutdown,
		SetTrace:                   setTrace,
		TextDocumentDidOpen:        textDocumentDidOpen,
		TextDocumentDidChange:      textDocumentDidChange,
		TextDocumentDidClose:       textDocumentDidClose,
		TextDocumentDidSave:        textDocumentDidSave,
		TextDocumentCompletion:     textDocumentCompletion,
		TextDocumentHover:          textDocumentHover,
		TextDocumentDefinition:     textDocumentDefinition,
		TextDocumentReferences:     textDocumentReferences,
		TextDocumentDocumentSymbol: textDocumentDocumentSymbol,
	}

	s := server.NewServer(&handler, lsName, true)
	s.RunStdio()
}

func initialize(context *glsp.Context, params *protocol.InitializeParams) (any, error) {
	commonlog.NewInfoMessage(0, "Initializing IATF Language Server...")

	capabilities := handler.CreateServerCapabilities()

	// Text document sync - full sync mode
	capabilities.TextDocumentSync = protocol.TextDocumentSyncKindFull

	// Completion support
	capabilities.CompletionProvider = &protocol.CompletionOptions{
		TriggerCharacters: []string{"{", "@"},
		ResolveProvider:   ptrBool(false),
	}

	// Hover support
	capabilities.HoverProvider = true

	// Go to definition support
	capabilities.DefinitionProvider = true

	// Find references support
	capabilities.ReferencesProvider = true

	// Document symbol support (outline)
	capabilities.DocumentSymbolProvider = true

	return protocol.InitializeResult{
		Capabilities: capabilities,
		ServerInfo: &protocol.InitializeResultServerInfo{
			Name:    lsName,
			Version: &version,
		},
	}, nil
}

func initialized(context *glsp.Context, params *protocol.InitializedParams) error {
	commonlog.NewInfoMessage(0, "IATF Language Server initialized")
	return nil
}

func shutdown(context *glsp.Context) error {
	commonlog.NewInfoMessage(0, "Shutting down IATF Language Server...")
	return nil
}

func setTrace(context *glsp.Context, params *protocol.SetTraceParams) error {
	return nil
}

func textDocumentDidOpen(context *glsp.Context, params *protocol.DidOpenTextDocumentParams) error {
	uri := params.TextDocument.URI
	content := params.TextDocument.Text

	documentStore.Open(uri, content)
	publishDiagnostics(context, uri)
	return nil
}

func textDocumentDidChange(context *glsp.Context, params *protocol.DidChangeTextDocumentParams) error {
	uri := params.TextDocument.URI

	// Full sync mode - take the last content change
	if len(params.ContentChanges) > 0 {
		content := params.ContentChanges[len(params.ContentChanges)-1].(protocol.TextDocumentContentChangeEventWhole).Text
		documentStore.Update(uri, content)
		publishDiagnostics(context, uri)
	}
	return nil
}

func textDocumentDidClose(context *glsp.Context, params *protocol.DidCloseTextDocumentParams) error {
	uri := params.TextDocument.URI
	documentStore.Close(uri)

	// Clear diagnostics
	context.Notify(protocol.ServerTextDocumentPublishDiagnostics, protocol.PublishDiagnosticsParams{
		URI:         uri,
		Diagnostics: []protocol.Diagnostic{},
	})
	return nil
}

func textDocumentDidSave(context *glsp.Context, params *protocol.DidSaveTextDocumentParams) error {
	// Re-validate on save
	uri := params.TextDocument.URI
	publishDiagnostics(context, uri)
	return nil
}

func publishDiagnostics(context *glsp.Context, uri protocol.DocumentUri) {
	doc := documentStore.Get(uri)
	if doc == nil {
		return
	}

	diagnostics := doc.GetDiagnostics()
	context.Notify(protocol.ServerTextDocumentPublishDiagnostics, protocol.PublishDiagnosticsParams{
		URI:         uri,
		Diagnostics: diagnostics,
	})
}

func textDocumentCompletion(context *glsp.Context, params *protocol.CompletionParams) (any, error) {
	uri := params.TextDocument.URI
	doc := documentStore.Get(uri)
	if doc == nil {
		return nil, nil
	}

	return doc.GetCompletions(params.Position), nil
}

func textDocumentHover(context *glsp.Context, params *protocol.HoverParams) (*protocol.Hover, error) {
	uri := params.TextDocument.URI
	doc := documentStore.Get(uri)
	if doc == nil {
		return nil, nil
	}

	return doc.GetHover(params.Position), nil
}

func textDocumentDefinition(context *glsp.Context, params *protocol.DefinitionParams) (any, error) {
	uri := params.TextDocument.URI
	doc := documentStore.Get(uri)
	if doc == nil {
		return nil, nil
	}

	return doc.GetDefinition(params.Position, uri), nil
}

func textDocumentReferences(context *glsp.Context, params *protocol.ReferenceParams) ([]protocol.Location, error) {
	uri := params.TextDocument.URI
	doc := documentStore.Get(uri)
	if doc == nil {
		return nil, nil
	}

	return doc.GetReferences(params.Position, uri), nil
}

func textDocumentDocumentSymbol(context *glsp.Context, params *protocol.DocumentSymbolParams) (any, error) {
	uri := params.TextDocument.URI
	doc := documentStore.Get(uri)
	if doc == nil {
		return nil, nil
	}

	return doc.GetDocumentSymbols(), nil
}

func ptrBool(b bool) *bool {
	return &b
}
