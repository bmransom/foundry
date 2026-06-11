use std::env;

fn greeting(name: &str) -> String {
    format!("Hello, {name}!")
}

fn main() {
    let name = env::args().nth(1).unwrap_or_else(|| "world".to_string());
    println!("{}", greeting(&name));
}

#[cfg(test)]
mod tests {
    use super::greeting;

    #[test]
    fn greeting_includes_the_name() {
        assert_eq!(greeting("Ada"), "Hello, Ada!");
    }
}
