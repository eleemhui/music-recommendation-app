import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchBar from "./SearchBar";

describe("SearchBar", () => {
  it("renders the input and button", () => {
    render(<SearchBar onSearch={vi.fn()} loading={false} />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /find songs/i })).toBeInTheDocument();
  });

  it("submit button is disabled when input is empty", () => {
    render(<SearchBar onSearch={vi.fn()} loading={false} />);
    expect(screen.getByRole("button", { name: /find songs/i })).toBeDisabled();
  });

  it("submit button becomes enabled when input has text", async () => {
    render(<SearchBar onSearch={vi.fn()} loading={false} />);
    await userEvent.type(screen.getByRole("textbox"), "sad songs");
    expect(screen.getByRole("button", { name: /find songs/i })).toBeEnabled();
  });

  it("calls onSearch with the trimmed phrase on submit", async () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} loading={false} />);
    await userEvent.type(screen.getByRole("textbox"), "  happy vibes  ");
    await userEvent.click(screen.getByRole("button", { name: /find songs/i }));
    expect(onSearch).toHaveBeenCalledOnce();
    expect(onSearch).toHaveBeenCalledWith("happy vibes");
  });

  it("does not call onSearch when input is only whitespace", async () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} loading={false} />);
    await userEvent.type(screen.getByRole("textbox"), "   ");
    // button stays disabled, but also test the submit guard directly
    const form = screen.getByRole("textbox").closest("form")!;
    form.dispatchEvent(new Event("submit", { bubbles: true }));
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("disables input and button while loading", () => {
    render(<SearchBar onSearch={vi.fn()} loading={true} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("shows spinner instead of button text when loading", () => {
    render(<SearchBar onSearch={vi.fn()} loading={true} />);
    expect(screen.queryByText(/find songs/i)).not.toBeInTheDocument();
    expect(document.querySelector(".spinner")).toBeInTheDocument();
  });
});
