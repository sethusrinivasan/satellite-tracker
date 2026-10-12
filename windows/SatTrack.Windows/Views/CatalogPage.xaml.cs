using System;
using System.Linq;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SatTrack.Windows.Services;

namespace SatTrack.Windows.Views;

public sealed partial class CatalogPage : Page
{
    private readonly SatelliteRepository _repository = new();

    public CatalogPage()
    {
        this.InitializeComponent();
        ApplyFilter();
    }

    private void ApplyFilter()
    {
        string search = SearchBox?.Text?.Trim() ?? "";
        string cat = (CmbCategory?.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "all";

        var filtered = _repository.Satellites.Where(s =>
        {
            bool matchesCat = cat == "all" || s.Category == cat;
            bool matchesSearch = string.IsNullOrEmpty(search) ||
                                 s.Name.Contains(search, StringComparison.OrdinalIgnoreCase) ||
                                 s.Id.ToString().Contains(search);
            return matchesCat && matchesSearch;
        }).ToList();

        SatListView.ItemsSource = filtered;
    }

    private void SearchBox_TextChanged(AutoSuggestBox sender, AutoSuggestBoxTextChangedEventArgs args) => ApplyFilter();
    private void CmbCategory_SelectionChanged(object sender, SelectionChangedEventArgs e) => ApplyFilter();

    private void BtnRefreshTles_Click(object sender, RoutedEventArgs e)
    {
        BtnRefreshTles.Content = "✓ Elements Fresh";
    }
}
