//go:build windows

package main

import "golang.org/x/sys/windows"

// isProcessRunning checks if a process with the given PID is running.
func isProcessRunning(pid int) bool {
	if pid <= 0 {
		return false
	}
	handle, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, uint32(pid))
	if err != nil {
		return false
	}
	windows.CloseHandle(handle)
	return true
}
