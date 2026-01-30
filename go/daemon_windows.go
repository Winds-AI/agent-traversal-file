//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"

	"golang.org/x/sys/windows"
)

// daemonSysProcAttr returns the syscall attributes for detaching the daemon process
func daemonSysProcAttr() *syscall.SysProcAttr {
	return &syscall.SysProcAttr{
		CreationFlags: windows.CREATE_NEW_PROCESS_GROUP | windows.DETACHED_PROCESS,
	}
}

const taskName = "IATF Daemon"

// isServiceInstalled checks if the daemon is installed as a Windows scheduled task
func isServiceInstalled() (bool, string) {
	cmd := exec.Command("schtasks", "/query", "/tn", taskName)
	if err := cmd.Run(); err == nil {
		return true, "schtasks"
	}
	return false, ""
}

func daemonInstallCommand() int {
	execPath, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting executable path: %v\n", err)
		return 1
	}

	// Create scheduled task that runs at logon
	cmd := exec.Command("schtasks",
		"/create",
		"/tn", taskName,
		"/tr", fmt.Sprintf(`"%s" daemon run`, execPath),
		"/sc", "onlogon",
		"/rl", "limited",
		"/f", // Force create (overwrite if exists)
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating scheduled task: %v\n%s\n", err, output)
		return 1
	}

	fmt.Println("Service installed (Windows Task Scheduler)")
	fmt.Println("\nThe daemon will start automatically on logon.")
	fmt.Println("\nTo start now:")
	fmt.Println("  schtasks /run /tn \"IATF Daemon\"")
	fmt.Println("\nTo check status:")
	fmt.Println("  schtasks /query /tn \"IATF Daemon\"")
	return 0
}

func daemonUninstallCommand() int {
	// Stop running task first
	stopCmd := exec.Command("schtasks", "/end", "/tn", taskName)
	stopCmd.Run() // Ignore error - task may not be running

	// Delete the scheduled task
	cmd := exec.Command("schtasks", "/delete", "/tn", taskName, "/f")
	output, err := cmd.CombinedOutput()
	if err != nil {
		outputStr := string(output)
		if strings.Contains(outputStr, "cannot find") || strings.Contains(outputStr, "does not exist") {
			fmt.Println("Service not installed")
			return 0
		}
		fmt.Fprintf(os.Stderr, "Error removing scheduled task: %v\n%s\n", err, output)
		return 1
	}

	fmt.Println("Service uninstalled")
	return 0
}
