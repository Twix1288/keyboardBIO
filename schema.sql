-- Create Users Table
create table users (
  id uuid default gen_random_uuid() primary key,
  username text unique not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create Biometrics Table
create table biometrics (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references users(id) not null,
  transform_matrix json not null,
  mean_vector json not null,
  threshold float not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(user_id)
);
